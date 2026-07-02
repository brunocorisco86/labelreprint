import os
import re
import sqlite3
import pandas as pd
import unicodedata
from dotenv import load_dotenv
from src.pdf.writer import PDFLabelWriter

load_dotenv()

# Caminho raiz do projeto dinâmico
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(PROJECT_ROOT, "data/processed/entregas_processadas.db"))
EXPORT_DIR = os.getenv("EXPORT_DIR", os.path.join(PROJECT_ROOT, "Export"))
DEFAULT_SHELF_LIFE = int(os.getenv("SHELF_LIFE_DAYS", "60"))

def sanitize_folder_name(name):
    """
    Sanitiza strings para nomes de pastas seguros no Linux:
    Remove acentos, caracteres especiais e substitui espaços por underscores.
    """
    if not name:
        return "NAO_INFORMADO"
    # Normaliza acentuações (ex: "Ateção" -> "Atecao")
    nfkd = unicodedata.normalize('NFKD', str(name))
    cleaned = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Remove caracteres especiais que não sejam alfanuméricos, espaços, hífens ou underscores
    cleaned = re.sub(r'[^a-zA-Z0-9_\-\s]', '', cleaned)
    # Substitui espaços e múltiplas underscores por um único underscore
    cleaned = re.sub(r'[\s_]+', '_', cleaned.strip())
    return cleaned

class BatchGenerator:
    """
    Classe responsável por coordenar a geração em lote de rótulos retroativos
    a partir das entregas registradas no banco SQLite, salvando os PDFs gerados
    na estrutura hierárquica correta e gerando o índice index.csv.
    """

    def __init__(self, db_path=None, export_dir=None, delete_individuals=False):
        self.db_path = db_path or DATABASE_PATH
        self.export_dir = export_dir or EXPORT_DIR
        self.writer = PDFLabelWriter()
        self.delete_individuals = delete_individuals

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def generate_all(self, shelf_life_days=None, limit=None, tipo_racao_filtro=None, lotes_filtro=None):
        """
        Executa a geração dos rótulos em lote.
        Permite customizar os dias de validade e limitar a quantidade de registros (para testes).
        """
        days = shelf_life_days if shelf_life_days is not None else DEFAULT_SHELF_LIFE
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Banco de dados de entregas não encontrado em: {self.db_path}. Execute o ETL primeiro.")
            
        conn = self.get_connection()
        query = "SELECT * FROM EntregasRacao"
        if limit:
            query += f" LIMIT {limit}"
            
        df_entregas = pd.read_sql(query, conn)
        conn.close()
        
        # Filtragem por tipo de ração (GlobalGap ou Comum) se aplicável
        if tipo_racao_filtro:
            tipo_filtro_limpo = str(tipo_racao_filtro).upper()
            df_entregas = df_entregas[df_entregas['TipoRacao'].astype(str).str.upper() == tipo_filtro_limpo]
            
        # Filtragem por lotes específicos (para geração sob demanda/filtro de núcleo)
        if lotes_filtro:
            df_entregas = df_entregas[df_entregas['FazendaLote'].isin(lotes_filtro)]
        
        total_records = len(df_entregas)
        filtro_msg = f" (Filtro Tipo: {tipo_racao_filtro})" if tipo_racao_filtro else ""
        print(f"[Generator] Iniciando geração de {total_records} rótulos{filtro_msg} com shelf-life de {days} dias...")
        
        index_records = []
        success_count = 0
        error_count = 0
        
        for idx, row in df_entregas.iterrows():
            id_rotulo = row['id_rotulo']
            if pd.isna(id_rotulo) or not id_rotulo:
                continue
            template = row['TemplatePDF']
            data_fab = row['Data']
            lote = row['Lote']
            
            # 1. Determina as pastas hierárquicas sanitizadas
            # Estrutura: Export/{Extensionista}/{TipoRacao}/{NomeFazenda}/{FazendaLote}/{id_rotulo}.pdf
            ext_folder = sanitize_folder_name(row['Extensionista'])
            
            # Traduz TipoRacao para nome de pasta amigável
            tipo_folder = "GlobalGap" if row['TipoRacao'] == "GG" else "Comum"
            
            # Sanitiza nome da fazenda e o lote composto (FazendaLote)
            fazenda_folder = sanitize_folder_name(row['NomeFazenda'])
            lote_composto_folder = sanitize_folder_name(row['FazendaLote'])
            
            # Monta o caminho final
            relative_dir = os.path.join(ext_folder, tipo_folder, fazenda_folder, lote_composto_folder)
            target_dir = os.path.join(self.export_dir, relative_dir)
            pdf_filename = f"{id_rotulo}.pdf"
            output_path = os.path.join(target_dir, pdf_filename)
            
            # 2. Executa a escrita no PDF
            try:
                self.writer.write_label(
                    template_name=template,
                    data_fabricacao_raw=data_fab,
                    lote=lote,
                    shelf_life_days=days,
                    output_path=output_path
                )
                success_count += 1
                
                # Registra no índice (guardamos caminhos relativos ao Export para portabilidade)
                relative_file_path = os.path.join(relative_dir, pdf_filename)
                index_records.append({
                    "id_rotulo": id_rotulo,
                    "caminho_arquivo": relative_file_path,
                    "data_fabricacao": data_fab,
                    "lote": lote,
                    "fazenda": row['Fazenda'],
                    "nome_fazenda": row['NomeFazenda'],
                    "extensionista": row['Extensionista'],
                    "tipo_racao": row['TipoRacao'],
                    "fabrica": row['FabricaRacao']
                })
                
                # Log de progresso a cada 100 registros
                if success_count % 100 == 0:
                    print(f"  [Progresso] {success_count}/{total_records} PDFs gerados com sucesso...")
                    
            except Exception as e:
                error_count += 1
                print(f"  [Erro] Falha ao gerar rótulo {id_rotulo}: {e}")

        # 3. Gera o arquivo de índice consolidado index.csv
        if index_records:
            df_index = pd.DataFrame(index_records)
            index_path = os.path.join(self.export_dir, "index.csv")
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            df_index.to_csv(index_path, index=False, encoding="utf-8")
            print(f"[Generator] Arquivo de índice consolidado gerado com sucesso em: {index_path}")
            
        # 4. Gera o arquivo sumario_entregas.txt e mescla os PDFs em cada pasta de lote, agrupados por Extensionista em ordem alfabética
        if not df_entregas.empty:
            print("[Generator] Iniciando geração dos sumários e mesclagem de PDFs por lote (ordenado por Extensionista)...")
            
            # Agrupa por Extensionista e ordena as chaves (nomes dos extensionistas)
            grouped_by_ext = df_entregas.groupby("Extensionista")
            sorted_extensionistas = sorted(grouped_by_ext.groups.keys(), key=lambda x: str(x).upper())
            
            for extensionista in sorted_extensionistas:
                df_ext = grouped_by_ext.get_group(extensionista)
                print(f"\n[Extensionista] Iniciando processamento dos lotes de: {extensionista}")
                
                # Agrupa os lotes do extensionista
                for fazenda_lote, group in df_ext.groupby("FazendaLote"):
                    first_row = group.iloc[0]
                    ext_folder = sanitize_folder_name(first_row['Extensionista'])
                    tipo_folder = "GlobalGap" if first_row['TipoRacao'] == "GG" else "Comum"
                    fazenda_folder = sanitize_folder_name(first_row['NomeFazenda'])
                    lote_composto_folder = sanitize_folder_name(first_row['FazendaLote'])
                    
                    target_dir = os.path.join(self.export_dir, ext_folder, tipo_folder, fazenda_folder, lote_composto_folder)
                    
                    # Se o diretório foi criado (porque geramos PDFs para ele), cria o sumário e faz a mesclagem
                    if os.path.exists(target_dir):
                        sumario_path = os.path.join(target_dir, "sumario_entregas.txt")
                        try:
                            self._write_sumario(group, sumario_path)
                        except Exception as e:
                            print(f"  [Erro] Falha ao gerar sumário para o lote {fazenda_lote}: {e}")
                            
                        try:
                            self._merge_pdfs_lote(group, target_dir)
                            print(f"✔️ [Status] Lote {fazenda_lote} do Extensionista {extensionista} concluído e pronto para impressão.")
                        except Exception as e:
                            print(f"  [Erro] Falha ao mesclar PDFs para o lote {fazenda_lote}: {e}")
                            
                print(f"✨ [Concluído] Todos os lotes do Extensionista {extensionista} foram gerados e mesclados!")
            
        print(f"[Generator] Fim da execução. Sucesso: {success_count} | Erros: {error_count}")
        return success_count, error_count

    def _write_sumario(self, df_lote, output_path):
        """
        Gera um arquivo de texto resumindo as entregas, retornos, sobras e transferências do lote.
        """
        import re
        # Ordena cronologicamente para exibição no sumário
        df_sorted = df_lote.sort_values(by=['Data', 'HoraTransacao', 'id_rotulo']).reset_index(drop=True)
        
        first_row = df_sorted.iloc[0]
        fazenda_lote = first_row['FazendaLote']
        nome_fazenda = first_row['NomeFazenda']
        extensionista = first_row['Extensionista']
        tipo_racao = "GlobalGap" if first_row['TipoRacao'] == "GG" else "Comum"
        
        # Listas para separar as tabelas
        entregas_list = []
        retornos_list = []
        
        total_entregue = 0.0
        total_retorno_sobra = 0.0
        total_transferencia_entrada = 0.0
        total_transferencia_saida = 0.0
        
        # Consolidação por fase
        soma_por_fase = {}
        
        for _, row in df_sorted.iterrows():
            data_str = row['Data']
            fase = row['FaseRacao']
            volume = float(row['QuantidadeEntregue'])
            status = row['StatusEntrega']
            num_carga = row['NumCarga']
            obs = str(row['ObsFrete']).upper() if not pd.isna(row['ObsFrete']) else ""
            
            # Identificação do Tipo de Transação
            cod_trans = str(row['CodigoTransacao']).upper() if not pd.isna(row['CodigoTransacao']) else ""
            num_ref_retorno = row['NumRefRetorno']
            valor_remessa = float(row['ValorRemessa']) if not pd.isna(row['ValorRemessa']) else 0.0
            nome_veiculo = str(row['NomeVeiculo']).upper() if not pd.isna(row['NomeVeiculo']) else ""
            
            # Identifica aviário de destino em caso de transferência
            destino_aviario = "Não identificado"
            if "TRANSF" in obs or "REMANEJ" in obs:
                match = re.search(r"AV[\.\s]*([0-9]+(?:[\-\/][0-9]+)*)", obs, re.IGNORECASE)
                if match:
                    destino_aviario = f"Aviário {match.group(1).strip()}"
            
            # Regras de Classificação
            # 1. Recolha de Sobra de Ração (Ração Abate no final do lote)
            if pd.notna(num_ref_retorno) and cod_trans == 'CRÉDITO' and valor_remessa < 0 and nome_veiculo == 'X' and fase == '5_ABATE':
                tipo_t = "Sobra/Rec."
                total_retorno_sobra += volume
                retornos_list.append((data_str, tipo_t, fase, volume, status, num_carga, obs, destino_aviario))
            # 2. Problema de Processo / Anomalia (Ração diferente de Abate nas condições de recolha)
            elif pd.notna(num_ref_retorno) and cod_trans == 'CRÉDITO' and valor_remessa < 0 and nome_veiculo == 'X' and fase != '5_ABATE':
                tipo_t = "Retorno/Err"
                total_retorno_sobra += volume
                retornos_list.append((data_str, tipo_t, fase, volume, status, num_carga, obs, destino_aviario))
            # 3. Transferência Interna - Saída (Volume negativo ou texto indicando transferência)
            elif volume < 0 and ("TRANSF" in obs or "REMANEJ" in obs):
                tipo_t = "Transf. Sai"
                total_transferencia_saida += volume
                retornos_list.append((data_str, tipo_t, fase, volume, status, num_carga, obs, destino_aviario))
            # 4. Retornos/Devoluções normais
            elif cod_trans == 'DEVOLUÇÃO' or cod_trans == 'CRÉDITO' or volume < 0:
                tipo_t = "Devol/Ret"
                total_retorno_sobra += volume
                retornos_list.append((data_str, tipo_t, fase, volume, status, num_carga, obs, destino_aviario))
            # 5. Transferência Interna - Entrada
            elif volume > 0 and ("TRANSF" in obs or "REMANEJ" in obs):
                tipo_t = "Transf. Ent"
                total_transferencia_entrada += volume
                entregas_list.append((data_str, tipo_t, fase, volume, status, num_carga, obs))
            # 6. Entrega Padrão
            else:
                tipo_t = "Entrega"
                total_entregue += volume
                entregas_list.append((data_str, tipo_t, fase, volume, status, num_carga, obs))
            
            # Acumula por fase
            soma_por_fase[fase] = soma_por_fase.get(fase, 0.0) + volume
        
        # Contagem e consolidação das ocorrências especiais
        sobras_count = 0
        sobras_volume = 0.0
        
        transf_count = 0
        transf_volume = 0.0
        transf_destinos = set()
        
        devol_count = 0
        devol_volume = 0.0
        
        for data_str, tipo_t, fase, volume, status, num_carga, obs, dest in retornos_list:
            if tipo_t == "Sobra/Rec.":
                sobras_count += 1
                sobras_volume += volume
            elif tipo_t == "Transf. Sai":
                transf_count += 1
                transf_volume += volume
                if dest != "Não identificado":
                    transf_destinos.add(dest)
            else: # Devol/Ret ou Retorno/Err
                devol_count += 1
                devol_volume += volume

        # Obter informações do lote de FiltroLotesAtivos
        status_lote_str = "Não Informado"
        abatido_str = "Não Informado"
        idade_lote_str = None
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT StatusLoteMtech, DataAlojamento, LoteAbatido FROM FiltroLotesAtivos WHERE FazendaLote = ?", (fazenda_lote,))
            row_filtro = cursor.fetchone()
            conn.close()
            
            if row_filtro:
                status_mtech, data_aloj_str, lote_abatido_val = row_filtro
                status_lote_str = "Aberto" if status_mtech == "Ativo" else "Fechado"
                abatido_str = "Sim" if lote_abatido_val == 1 else "Não"
                
                if lote_abatido_val == 0 and data_aloj_str:
                    try:
                        from datetime import datetime
                        dt_aloj = datetime.strptime(data_aloj_str, '%Y-%m-%d')
                        dt_agora = datetime.now()
                        dias = (dt_agora - dt_aloj).days
                        if dias < 0:
                            # Fallback para 2026-07-01 se a data do sistema estiver no passado em relação ao alojamento
                            dt_ref = datetime(2026, 7, 1)
                            dias = (dt_ref - dt_aloj).days
                        idade_lote_str = f"{dias} dias"
                    except Exception as ex:
                        print(f"Erro ao calcular idade do lote: {ex}")
        except Exception as e:
            print(f"Erro ao ler FiltroLotesAtivos no sumário: {e}")

        # Montagem do arquivo txt
        lines = []
        lines.append("=========================================================================")
        lines.append(f"SUMÁRIO DE TRANSAÇÕES DE RAÇÃO - LOTE: {fazenda_lote}")
        lines.append("=========================================================================")
        lines.append(f"Fazenda/Aviário : {nome_fazenda} (Código: {first_row['Fazenda']})")
        lines.append(f"Extensionista   : {extensionista}")
        lines.append(f"Classificação   : {tipo_racao}")
        lines.append("---")
        lines.append(f"Status          : {status_lote_str}")
        lines.append(f"Abatido         : {abatido_str}")
        if idade_lote_str:
            lines.append(f"Idade do Lote   : {idade_lote_str}")
        lines.append("=========================================================================\n")
        
        # 1. Tabela Principal (Entregas e Recebimentos)
        lines.append("=========================================================================")
        lines.append("📥 ENTREGAS E RECEBIMENTOS DE RAÇÃO (CONSUMO EFETIVO)")
        lines.append("=========================================================================")
        lines.append("-------------------------------------------------------------------------")
        lines.append(f"{'Data':<10} | {'Tipo':<11} | {'Fase Ração':<15} | {'Volume (kg)':<11} | {'Status':<10} | {'Carga/Info':<15}")
        lines.append("-------------------------------------------------------------------------")
        
        for data_str, tipo_t, fase, volume, status, num_carga, obs in entregas_list:
            vol_str = f"{volume:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
            lines.append(f"{data_str:<10} | {tipo_t:<11} | {fase:<15} | {vol_str:>11} | {status:<10} | Carga: {num_carga}")
            if obs and len(obs) > 5:
                obs_clean = obs.replace("\n", " ").strip()
                if len(obs_clean) > 60:
                    obs_clean = obs_clean[:57] + "..."
                lines.append(f"   [Obs]: {obs_clean}")
        lines.append("-------------------------------------------------------------------------\n")
        
        # 2. Seção Separada para Devoluções, Recolhas e Transferências (Saídas)
        if retornos_list:
            lines.append("=========================================================================")
            lines.append("🔄 RETORNOS, DEVOLUÇÕES E TRANSFERÊNCIAS (SAÍDAS / CRÉDITOS)")
            lines.append("=========================================================================")
            lines.append("-------------------------------------------------------------------------")
            lines.append(f"{'Data':<10} | {'Tipo':<11} | {'Fase Ração':<15} | {'Volume (kg)':<11} | {'Destino/Ref':<15} | {'Carga/Ref':<10}")
            lines.append("-------------------------------------------------------------------------")
            for data_str, tipo_t, fase, volume, status, num_carga, obs, dest in retornos_list:
                vol_str = f"{volume:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
                lines.append(f"{data_str:<10} | {tipo_t:<11} | {fase:<15} | {vol_str:>11} | {dest:<15} | Carga: {num_carga}")
                if obs and len(obs) > 5:
                    obs_clean = obs.replace("\n", " ").strip()
                    if len(obs_clean) > 60:
                        obs_clean = obs_clean[:57] + "..."
                    lines.append(f"   [Obs/Motivo]: {obs_clean}")
            lines.append("-------------------------------------------------------------------------\n")

        def format_kg(val):
            return f"{val:,.1f} kg".replace(",", "X").replace(".", ",").replace("X", ".")

        # 3. Sumário de Ocorrências Especiais
        lines.append("=========================================================================")
        lines.append("📋 SUMÁRIO DE OCORRÊNCIAS ESPECIAIS (SOBRAS / TRANSFERÊNCIAS / DEVOLUÇÕES)")
        lines.append("=========================================================================")
        
        # Sobras
        if sobras_count > 0:
            lines.append(f"- Sobras de ração recolhidas: {sobras_count} carga(s) | Volume total: {format_kg(sobras_volume)}")
        else:
            lines.append("- Sobras de ração           : Não houve sobras recolhidas neste lote.")
            
        # Transferências
        if transf_count > 0:
            dest_str = ", ".join(sorted(transf_destinos)) if transf_destinos else "Não identificado"
            lines.append(f"- Transferências realizadas : {transf_count} ocorrência(s) | Volume total: {format_kg(transf_volume)}")
            lines.append(f"  [Destino]: {dest_str}")
        else:
            lines.append("- Transferências realizadas : Não houve transferências de saída neste lote.")
            
        # Devoluções/Retornos
        if devol_count > 0:
            lines.append(f"- Devoluções / Retornos     : {devol_count} ocorrência(s) | Volume total: {format_kg(devol_volume)}")
        else:
            lines.append("- Devoluções / Retornos     : Não houve devoluções ou retornos operacionais neste lote.")
        lines.append("=========================================================================\n")
        
        # 4. Totais Consolidados
        saldo_liquido = total_entregue + total_retorno_sobra + total_transferencia_entrada + total_transferencia_saida
        
        lines.append("=========================================================================")
        lines.append("📊 BALANÇO CONSOLIDADO DO LOTE")
        lines.append("=========================================================================")
        
        lines.append(f"Total Entregue (Cargas Normais)    : {format_kg(total_entregue)}")
        if total_transferencia_entrada > 0:
            lines.append(f"Total Transferências (Entrada)    : {format_kg(total_transferencia_entrada)}")
        if total_transferencia_saida < 0:
            lines.append(f"Total Transferências (Saída)      : {format_kg(total_transferencia_saida)}")
        if total_retorno_sobra < 0:
            lines.append(f"Total Retornos / Sobras Recolhidas: {format_kg(total_retorno_sobra)}")
        lines.append("-------------------------------------------------------------------------")
        lines.append(f"SALDO LÍQUIDO CONSUMIDO NO LOTE   : {format_kg(saldo_liquido)}")
        lines.append("=========================================================================\n")
        
        # 4. Consumo Líquido por Fase
        lines.append("=========================================================================")
        lines.append("🌾 CONSUMO LÍQUIDO POR FASE DE RAÇÃO")
        lines.append("=========================================================================")
        for fase_nome in sorted(soma_por_fase.keys()):
            fase_vol = soma_por_fase[fase_nome]
            lines.append(f"{fase_nome:<20} : {format_kg(fase_vol)}")
        lines.append("=========================================================================")
        
        # Grava o arquivo de texto
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _merge_pdfs_lote(self, df_lote, target_dir):
        """
        Mescla todos os PDFs de rótulos ativos de um lote em um único PDF
        no formato '{lote_composto}-{primeiro_nome_produtor}-{qtd_rotulos}.pdf',
        em ordem cronológica de data e hora de entrega, aplicando compressão.
        """
        from pypdf import PdfReader, PdfWriter
        
        # Filtra registros que geraram rótulo
        df_active = df_lote[df_lote['id_rotulo'].notna()].copy()
        if df_active.empty:
            return
            
        # Ordena cronologicamente por Data, HoraTransacao e id_rotulo
        df_sorted = df_active.sort_values(by=['Data', 'HoraTransacao', 'id_rotulo']).reset_index(drop=True)
        
        writer = PdfWriter()
        pdf_paths = []
        for _, row in df_sorted.iterrows():
            id_rotulo = row['id_rotulo']
            pdf_path = os.path.join(target_dir, f"{id_rotulo}.pdf")
            if os.path.exists(pdf_path):
                pdf_paths.append(pdf_path)
                
        if not pdf_paths:
            return
            
        for path in pdf_paths:
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
                
        # Aplica desduplicação de objetos idênticos apenas se houver mais de um arquivo mesclado
        if len(pdf_paths) > 1:
            writer.compress_identical_objects()
            
        first_row = df_sorted.iloc[0]
        fazenda_lote = first_row['FazendaLote']
        nome_fazenda = first_row['NomeFazenda']
        
        # Extrai e sanitiza o primeiro nome do produtor rural/fazenda
        partes_nome = str(nome_fazenda).strip().split()
        primeiro_nome = partes_nome[0] if partes_nome else "PRODUTOR"
        primeiro_nome_sanitizado = sanitize_folder_name(primeiro_nome)
        
        output_filename = f"{fazenda_lote}-{primeiro_nome_sanitizado}-{len(pdf_paths)}.pdf"
        output_merged_path = os.path.join(target_dir, output_filename)
        
        with open(output_merged_path, "wb") as f:
            writer.write(f)
        writer.close()
        print(f"  [Merge] Gerado PDF mesclado comprimido contendo {len(pdf_paths)} rótulos em: {output_merged_path}")
        
        # Deleta os PDFs individuais se configurado
        if self.delete_individuals:
            for path in pdf_paths:
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"  [Erro] Falha ao remover PDF individual {path}: {e}")


if __name__ == "__main__":
    # Teste rápido gerando os 10 primeiros rótulos no Export
    generator = BatchGenerator()
    try:
        print("[Teste] Gerando os 10 primeiros registros como teste...")
        generator.generate_all(limit=10)
    except Exception as e:
        print("[Teste] Falha no teste de lote:", e)
