import os
import sqlite3
import glob
import re
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Caminho raiz do projeto dinâmico
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(PROJECT_ROOT, "data/processed/entregas_processadas.db"))

class DataManager:
    """
    Classe responsável por processar os dados brutos de entregas, fazendas e regiões,
    gerar as features necessárias para a impressão dos rótulos e salvar tudo no banco de dados SQLite.
    """

    def __init__(self, db_path=None, raw_dir=None):
        self.db_path = db_path or DATABASE_PATH
        # Garante que a pasta de destino exista
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Define o diretório de dados brutos (prioriza data/raw, usa data/templates como fallback se não existir)
        if raw_dir:
            self.raw_dir = raw_dir
        else:
            default_raw_dir = os.path.join(PROJECT_ROOT, "data/raw")
            if os.path.exists(default_raw_dir):
                self.raw_dir = default_raw_dir
            else:
                self.raw_dir = os.path.join(PROJECT_ROOT, "data/templates")
        
        # Inicializa a tabela de Telegram
        self.init_telegram_table()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def normalize_fazenda_lote(self, fazenda_lote):
        """Normaliza a string FazendaLote para remover zeros à esquerda do lote e garantir formato padrão {fazenda}-{lote} (ex: '1342-05' -> '1342-5')"""
        if pd.isna(fazenda_lote):
            return None
        
        fazenda_lote_str = str(fazenda_lote).strip()
        if '-' in fazenda_lote_str:
            parts = fazenda_lote_str.split('-')
            try:
                fazenda_part = int(float(parts[0].strip()))
                lote_part = int(float(parts[-1].strip()))
                return f"{fazenda_part}-{lote_part}"
            except ValueError:
                return fazenda_lote_str
        return fazenda_lote_str

    def extract_lote(self, fazenda_lote):
        """Extrai o lote ordinal da string FazendaLote (ex: '1351-1' -> '01')"""
        if pd.isna(fazenda_lote):
            return "00"
        
        fazenda_lote_str = str(fazenda_lote).strip()
        if '-' in fazenda_lote_str:
            parts = fazenda_lote_str.split('-')
            lote_part = parts[-1].strip()
            # Tenta converter para int para preencher com zeros à esquerda
            try:
                lote_int = int(lote_part)
                return f"{lote_int:02d}"
            except ValueError:
                return lote_part
        return "00"

    def extract_fase_racao(self, nome_formula):
        """Mapeia o nome da fórmula para a fase da ração correspondente"""
        if pd.isna(nome_formula):
            return "DESCONHECIDA"
        
        nome = str(nome_formula).upper()
        if "PRE INICIAL" in nome or "PRE-INICIAL" in nome:
            return "1_PREINICIAL"
        elif "INICIAL II" in nome:
            return "3_INICIAL2"
        elif "INICIAL I" in nome:
            return "2_INICIAL1"
        elif "CRESCIMENTO" in nome:
            return "4_CRESCIMENTO"
        elif "ABATE" in nome:
            return "5_ABATE"
        return "OUTRA"

    def detect_factory(self, obs_frete):
        """Identifica a fábrica produtora da ração com base nas observações de frete"""
        if pd.isna(obs_frete):
            return "CVALE"
        
        obs = str(obs_frete).upper()
        if "COPACOL" in obs:
            return "COPACOL"
        elif "AGRIFIRM" in obs:
            return "AGRIFIRM"
        elif "LAR" in obs:
            return "LAR"
        elif "COAMO" in obs:
            return "COAMO"
        return "CVALE"

    def resolve_template_name(self, factory, fase, tipo_racao):
        """
        Seleciona o arquivo de template PDF com base na fábrica, fase e tipo de ração (CM ou GG).
        Se a fábrica de terceiros não possuir template específico, usa o template da CVALE como fallback.
        """
        # Se for terceiros, verifica se temos o template de crescimento comum
        if factory in ["COPACOL", "AGRIFIRM", "LAR", "COAMO"] and fase == "4_CRESCIMENTO" and tipo_racao == "CM":
            return f"{factory}_4_CRESCIMENTO_CM.pdf"
        
        # Caso contrário ou como fallback, usa os templates da CVALE
        # Mapeia fase inválida ou desconhecida para crescimento (fallback seguro)
        fase_limpa = fase if fase in ["1_PREINICIAL", "2_INICIAL1", "3_INICIAL2", "4_CRESCIMENTO", "5_ABATE"] else "4_CRESCIMENTO"
        tipo_limpo = tipo_racao if tipo_racao in ["CM", "GG"] else "CM"
        return f"CVALE_{fase_limpa}_{tipo_limpo}.pdf"

    def run_etl(self):
        """Executa todo o pipeline de ETL e salva os dados no SQLite"""
        print("[ETL] Iniciando carregamento dos dados brutos...")
        
        # 1. Carregar Regiões
        regioes_dir = os.path.join(self.raw_dir, "RegioesAtualizadas")
        csv_files = glob.glob(os.path.join(regioes_dir, "*.csv"))
        
        if not csv_files:
            raise FileNotFoundError(f"Nenhum arquivo CSV de regiões encontrado em: {regioes_dir}")
            
        # Função para extrair data do nome do arquivo (ex: "regioes_atualizadas_30_04_26.csv" -> 30/04/26)
        def get_file_date(filepath):
            filename = os.path.basename(filepath)
            # Busca padrões de data como DD.MM.YY ou DD_MM_YY no nome
            match = re.search(r'(\d{2})[._](\d{2})[._](\d{2})', filename)
            if match:
                try:
                    day, month, year = map(int, match.groups())
                    full_year = 2000 + year if year < 100 else year
                    return datetime(full_year, month, day)
                except ValueError:
                    pass
            # Fallback para a data de modificação física do arquivo
            return datetime.fromtimestamp(os.path.getmtime(filepath))
            
        # Seleciona o arquivo de regiões mais recente
        regioes_file = max(csv_files, key=get_file_date)
        print(f"[ETL] Lendo Regiões de: {regioes_file}")

        # Detecta o separador dinamicamente (vírgula ou ponto-e-vírgula)
        sep = ','
        try:
            with open(regioes_file, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                if ';' in first_line:
                    sep = ';'
        except Exception:
            pass

        df_regioes = pd.read_csv(regioes_file, sep=sep)

        # Mapeia colunas caso seja o formato de exportação original do Excel (com acentos e espaços)
        rename_map = {}
        if 'n° dos aviários' in df_regioes.columns:
            rename_map['n° dos aviários'] = 'Aviario'
        if 'Final' in df_regioes.columns:
            rename_map['Final'] = 'Extensionista'
        elif 'Ext' in df_regioes.columns:
            rename_map['Ext'] = 'Extensionista'
            
        if rename_map:
            df_regioes = df_regioes.rename(columns=rename_map)

        # Limpar chave Aviario
        df_regioes['Aviario'] = pd.to_numeric(df_regioes['Aviario'], errors='coerce')
        df_regioes = df_regioes.dropna(subset=['Aviario'])
        df_regioes['Aviario'] = df_regioes['Aviario'].astype(int)
        df_regioes['Extensionista'] = df_regioes['Extensionista'].fillna("Nao_Identificado").astype(str).str.strip()
        
        # 2. Carregar Filtro Lotes Ativos
        filtro_file = os.path.join(self.raw_dir, "FiltroLotesAtivos/FiltroLotesAtivos.xlsx")
        print(f"[ETL] Lendo Filtro de Lotes Ativos de: {filtro_file}")
        df_filtro = pd.read_excel(filtro_file)
        df_filtro['FazendaLote'] = (df_filtro['Fazenda'].astype(str) + '-' + df_filtro['Lote'].astype(str)).apply(self.normalize_fazenda_lote)
        # Formatar campos temporais e booleanos no filtro
        df_filtro['DataAlojamento'] = pd.to_datetime(df_filtro['DataAlojamento']).dt.strftime('%Y-%m-%d')
        df_filtro['DataAbate'] = pd.to_datetime(df_filtro['DataAbate']).dt.strftime('%Y-%m-%d')
        df_filtro['LoteAbatido'] = df_filtro['LoteAbatido'].astype(int)


        
        # 3. Carregar Fazendas
        fazendas_file = os.path.join(self.raw_dir, "ListagemGeralFazendas/ListagemGeralFazendas.xlsx")
        print(f"[ETL] Lendo Cadastro Geral de Fazendas de: {fazendas_file}")
        df_fazendas = pd.read_excel(fazendas_file)
        df_fazendas['Fazenda'] = pd.to_numeric(df_fazendas['Fazenda'], errors='coerce')
        df_fazendas = df_fazendas.dropna(subset=['Fazenda'])
        df_fazendas['Fazenda'] = df_fazendas['Fazenda'].astype(int)
        
        # Tratar coluna Global GAP para booleano
        df_fazendas['Granja Global GAP'] = df_fazendas['Granja Global GAP'].astype(str).str.upper()
        df_fazendas['Granja Global GAP'] = df_fazendas['Granja Global GAP'].isin(['VERDADEIRO', 'TRUE', '1', 'YES'])
        
        # 3. Carregar Entregas de Ração
        entregas_pattern = os.path.join(self.raw_dir, "EntregasRacao/*.xlsx")
        entregas_files = glob.glob(entregas_pattern)
        print(f"[ETL] Encontrados {len(entregas_files)} arquivos de entregas.")
        
        dfs_entregas = []
        for file in entregas_files:
            print(f"[ETL] Carregando entregas de: {file}")
            # Lemos apenas as colunas úteis para economizar memória e velocidade
            cols_to_use = [
                'Data', 'HoraTransacao', 'Formula', 'NomeFormula', 'Veiculo', 
                'StatusEntrega', 'NumCarga', 'FazendaLote', 'QuantidadeEntregue', 
                'Fazenda', 'NomeFazenda', 'ObsFrete', 'NotaFiscal', 'OrdemFabrica',
                'NomeVeiculo', 'CodigoTransacao', 'NumRefRetorno', 'ValorRemessa', 'TipoTransacao'
            ]
            df_temp = pd.read_excel(file, usecols=cols_to_use)
            dfs_entregas.append(df_temp)
            
        df_entregas = pd.concat(dfs_entregas, ignore_index=True)
        
        # Normalizar FazendaLote para remover diferenças de formatação/padding
        if 'FazendaLote' in df_entregas.columns:
            df_entregas['FazendaLote'] = df_entregas['FazendaLote'].apply(self.normalize_fazenda_lote)
        
        # Limpar registros sujos ou totalizadores (Fazenda deve ser numérica)
        df_entregas['Fazenda'] = pd.to_numeric(df_entregas['Fazenda'], errors='coerce')
        df_entregas = df_entregas.dropna(subset=['Fazenda'])
        df_entregas['Fazenda'] = df_entregas['Fazenda'].astype(int)
        
        # Garantir que colunas numéricas sejam devidamente convertidas para evitar concatenações estranhas
        df_entregas['QuantidadeEntregue'] = pd.to_numeric(df_entregas['QuantidadeEntregue'], errors='coerce').fillna(0.0)
        df_entregas['NumCarga'] = pd.to_numeric(df_entregas['NumCarga'], errors='coerce').fillna(0).astype(int)
        df_entregas['OrdemFabrica'] = pd.to_numeric(df_entregas['OrdemFabrica'], errors='coerce').fillna(0).astype(int)
        df_entregas['NotaFiscal'] = pd.to_numeric(df_entregas['NotaFiscal'], errors='coerce').fillna(0).astype(int)
        df_entregas['Formula'] = pd.to_numeric(df_entregas['Formula'], errors='coerce').fillna(0).astype(int)
        
        # Filtrar apenas entregas concluídas
        df_entregas = df_entregas[df_entregas['StatusEntrega'].astype(str).str.upper() == 'CONCLUÍDO']
        
        # Desduplicar registros 100% repetidos operacionalmente
        initial_len = len(df_entregas)
        df_entregas = df_entregas.drop_duplicates(subset=[
            'FazendaLote', 'Data', 'HoraTransacao', 'NumCarga', 
            'QuantidadeEntregue', 'CodigoTransacao', 'NomeFormula'
        ])
        print(f"[ETL] Removidos {initial_len - len(df_entregas)} registros duplicados idênticos.")
        
        # 4. Enriquecimento de Dados (Joins e Features)
        print("[ETL] Enriquecendo dados e criando features...")
        
        # Juntar com Fazendas para saber se é GlobalGap
        df_entregas = df_entregas.merge(
            df_fazendas[['Fazenda', 'Granja Global GAP']], 
            on='Fazenda', 
            how='left'
        )
        # Se não achar no cadastro, assume Falso
        df_entregas['Granja Global GAP'] = df_entregas['Granja Global GAP'].fillna(False)
        df_entregas['TipoRacao'] = np.where(df_entregas['Granja Global GAP'], 'GG', 'CM')
        
        # Juntar com Regiões para obter o Extensionista nominal
        df_entregas = df_entregas.merge(
            df_regioes[['Aviario', 'Extensionista']], 
            left_on='Fazenda', 
            right_on='Aviario', 
            how='left'
        )
        df_entregas['Extensionista'] = df_entregas['Extensionista'].fillna("Nao_Identificado")
        # Remove a coluna duplicada do join
        if 'Aviario' in df_entregas.columns:
            df_entregas = df_entregas.drop(columns=['Aviario'])
            
        # Extrair Lote
        df_entregas['Lote'] = df_entregas['FazendaLote'].apply(self.extract_lote)
        
        # Filtrar apenas entregas que constem na planilha FiltroLotesAtivos
        lotes_ativos = df_filtro['FazendaLote'].tolist()
        antes_filtro_lotes = len(df_entregas)
        df_entregas = df_entregas[df_entregas['FazendaLote'].isin(lotes_ativos)].reset_index(drop=True)
        depois_filtro_lotes = len(df_entregas)
        print(f"[ETL] Filtradas {antes_filtro_lotes - depois_filtro_lotes} entregas que não constam no FiltroLotesAtivos. Mantidas {depois_filtro_lotes} entregas.")
        
        # Extrair Fase Ração
        df_entregas['FaseRacao'] = df_entregas['NomeFormula'].apply(self.extract_fase_racao)
        
        # Detectar Fábrica de Ração
        df_entregas['FabricaRacao'] = df_entregas['ObsFrete'].apply(self.detect_factory)
        
        # Tratar Data
        df_entregas['Data'] = pd.to_datetime(df_entregas['Data']).dt.strftime('%Y-%m-%d')
        
        # Selecionar template PDF correspondente
        df_entregas['TemplatePDF'] = df_entregas.apply(
            lambda row: self.resolve_template_name(row['FabricaRacao'], row['FaseRacao'], row['TipoRacao']), 
            axis=1
        )
        
        # Filtrar anomalias de sobra de lote anterior (cargas fora de ordem):
        # Quando cargas de fases tardias (como 3_INICIAL2 ou 5_ABATE) ocorrem antes de cargas de fases iniciais (como 1_PREINICIAL)
        # no mesmo lote, elas são consideradas sobras do ciclo/lote anterior lançadas tardiamente e devem ser descartadas.
        df_entregas = df_entregas.sort_values(by=['FazendaLote', 'Data', 'HoraTransacao']).reset_index(drop=True)
        
        # Mapeamento ordinal para avaliar a ordem cronológica correta das fases
        fase_ordinais = {
            '1_PREINICIAL': 1,
            '2_INICIAL1': 2,
            '3_INICIAL2': 3,
            '4_CRESCIMENTO': 4,
            '5_ABATE': 5
        }
        df_entregas['temp_fase_ord'] = df_entregas['FaseRacao'].map(fase_ordinais).fillna(0).astype(int)
        
        # Identifica para cada entrega qual a menor fase legítima que ocorre subsequentemente no mesmo lote.
        # Usamos cummin de trás para frente (invertendo o DataFrame) e shiftando 1 linha.
        df_entregas['temp_min_subsequente'] = (
            df_entregas.iloc[::-1]
            .groupby('FazendaLote')['temp_fase_ord']
            .transform(lambda x: x.cummin().shift(1).fillna(99))
            .iloc[::-1]
        )
        
        # Se a menor fase subsequente for menor que a fase da entrega atual (e maior que zero para ignorar fases desconhecidas),
        # significa que a entrega atual está fora de ordem (fase mais velha vindo antes de fase mais nova).
        condicao_sobra_anterior = (
            (df_entregas['temp_min_subsequente'] > 0) &
            (df_entregas['temp_min_subsequente'] < df_entregas['temp_fase_ord'])
        )
        
        antes_filtro = len(df_entregas)
        df_entregas = df_entregas[~condicao_sobra_anterior].reset_index(drop=True)
        depois_filtro = len(df_entregas)
        print(f"[ETL] Filtradas {antes_filtro - depois_filtro} ocorrências de cargas de ração fora de ordem (sobras do lote anterior).")
        
        df_entregas = df_entregas.drop(columns=['temp_fase_ord', 'temp_min_subsequente'])

        # Inicializa GeraRotulo como True para entregas normais e False para devoluções/saídas
        df_entregas['GeraRotulo'] = df_entregas['QuantidadeEntregue'] > 0
        
        # 1. Filtra devoluções integrais: se a quantidade líquida por carga (NumCarga) for <= 0, desmarca GeraRotulo
        carga_liquida = df_entregas.groupby('NumCarga')['QuantidadeEntregue'].sum().reset_index()
        cargas_zeradas = carga_liquida[carga_liquida['QuantidadeEntregue'] <= 0]['NumCarga'].tolist()
        df_entregas.loc[df_entregas['NumCarga'].isin(cargas_zeradas), 'GeraRotulo'] = False
        
        # 2. Evita duplicidade de rótulos no mesmo dia para a mesma ração no mesmo lote
        df_entregas = df_entregas.sort_values(by=['FazendaLote', 'Data', 'HoraTransacao']).reset_index(drop=True)
        df_entregas['temp_row_id'] = range(len(df_entregas))
        
        df_ativas = df_entregas[df_entregas['GeraRotulo'] == True].copy()
        df_ativas['keep_label'] = ~df_ativas.duplicated(subset=['FazendaLote', 'Data', 'FaseRacao'], keep='first')
        
        row_ids_para_remover = df_ativas[df_ativas['keep_label'] == False]['temp_row_id'].tolist()
        df_entregas.loc[df_entregas['temp_row_id'].isin(row_ids_para_remover), 'GeraRotulo'] = False
        
        # 3. Calcula o sequencial ordinal seq_lote apenas para as entregas ativas (GeraRotulo == True)
        df_ativas_finais = df_entregas[df_entregas['GeraRotulo'] == True].copy()
        df_ativas_finais = df_ativas_finais.sort_values(by=['FazendaLote', 'Data', 'HoraTransacao']).reset_index(drop=True)
        df_ativas_finais['seq_lote'] = df_ativas_finais.groupby('FazendaLote').cumcount() + 1
        
        df_entregas = df_entregas.merge(df_ativas_finais[['temp_row_id', 'seq_lote']], on='temp_row_id', how='left')
        
        # 4. Criar ID do Rótulo Único Determinístico apenas para ativos
        def build_label_id(row):
            if pd.isna(row['seq_lote']):
                return None
            
            try:
                dt_obj = datetime.strptime(row['Data'], '%Y-%m-%d')
                dt_str = dt_obj.strftime('%d%m%y')
            except Exception:
                dt_str = "000000"
            
            seq_str = f"{int(row['seq_lote']):02d}"
            aviario_str = f"AV{row['Fazenda']}"
            return f"{seq_str}_{row['TipoRacao']}_{aviario_str}_{row['Lote']}_{dt_str}"
            
        df_entregas['id_rotulo'] = df_entregas.apply(build_label_id, axis=1)
        
        # Limpar colunas auxiliares
        df_entregas = df_entregas.drop(columns=['temp_row_id', 'seq_lote'])
        
        # 5. Salvar no Banco de Dados SQLite
        print(f"[ETL] Salvando dados processados em SQLite: {self.db_path}...")
        conn = self.get_connection()
        try:
            # Salvar tabela fato de Entregas
            df_entregas.to_sql("EntregasRacao", conn, if_exists="replace", index=False)
            
            # Salvar tabela dimensão de Fazendas
            # Filtra colunas de Fazendas para as principais de cadastro
            fazendas_cols = [
                'Fazenda', 'Nome Fazenda', 'Granja Global GAP', 'Ativo', 
                'Capacidade Cabeças', 'Cidade', 'Extensionista', 'Código BP Propriedade'
            ]
            # Filtra apenas colunas existentes no df_fazendas
            existing_fazendas_cols = [c for c in fazendas_cols if c in df_fazendas.columns]
            df_fazendas_dim = df_fazendas[existing_fazendas_cols].drop_duplicates(subset=['Fazenda'])
            df_fazendas_dim.to_sql("Fazendas", conn, if_exists="replace", index=False)
            
            # Salvar tabela dimensão de Regiões
            df_regioes.to_sql("Regioes", conn, if_exists="replace", index=False)
            
            # Salvar tabela dimensão de FiltroLotesAtivos
            df_filtro.to_sql("FiltroLotesAtivos", conn, if_exists="replace", index=False)
            print("[ETL] Tabela FiltroLotesAtivos salva com sucesso no SQLite.")
            

            
            print("[ETL] ETL executado com sucesso e tabelas criadas no banco de dados!")
        finally:
            conn.close()

    def init_telegram_table(self):
        """Inicializa a tabela UsuariosTelegram no SQLite para associar telegram_id e emails"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS UsuariosTelegram (
                    telegram_id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL,
                    username TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        except Exception as e:
            print(f"[DataManager] Erro ao inicializar tabela de Telegram: {e}")
        finally:
            conn.close()

    def get_telegram_user(self, telegram_id):
        """Retorna o e-mail cadastrado para o telegram_id ou None"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT email FROM UsuariosTelegram WHERE telegram_id = ?", (telegram_id,))
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            print(f"[DataManager] Erro ao buscar usuário do Telegram: {e}")
            return None
        finally:
            conn.close()

    def save_telegram_user(self, telegram_id, email, username=None):
        """Salva ou atualiza a associação telegram_id -> email"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO UsuariosTelegram (telegram_id, email, username, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(telegram_id) DO UPDATE SET
                    email = excluded.email,
                    username = excluded.username,
                    updated_at = CURRENT_TIMESTAMP
            """, (telegram_id, email.strip().lower(), username))
            conn.commit()
            return True
        except Exception as e:
            print(f"[DataManager] Erro ao salvar usuário do Telegram: {e}")
            return False
        finally:
            conn.close()

if __name__ == "__main__":
    manager = DataManager()
    manager.run_etl()
