import os
import sqlite3
import random
import pytest
import json
import pandas as pd
from src.core.generator import BatchGenerator, sanitize_folder_name
from src.pdf.writer import PDFLabelWriter

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/processed/entregas_processadas.db")

def test_generate_selected_lotes(tmp_path):
    """
    Teste ampliado para selecionar pelo menos 20 aviários-lotes (FazendaLote) distintos,
    envolvendo pelo menos 5 extensionistas diferentes, e cobrindo os fornecedores
    disponíveis (CVALE, COPACOL, AGRIFIRM, LAR) e ambos os tipos de ração (GG e CM).
    Gera todos os PDFs e valida sua corretude em uma pasta temporária.
    """
    # 1. Verifica se o banco de dados de entregas existe
    assert os.path.exists(DATABASE_PATH), f"Banco de dados não encontrado em {DATABASE_PATH}. Execute o ETL primeiro."
    
    # 2. Conecta ao banco de dados para selecionar os lotes com base nas regras
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Busca todas as entregas distintas com seus templates e extensionistas
        query = """
            SELECT DISTINCT Extensionista, TipoRacao, FazendaLote, TemplatePDF 
            FROM EntregasRacao
            WHERE Extensionista IS NOT NULL 
              AND TipoRacao IS NOT NULL 
              AND FazendaLote IS NOT NULL
              AND TemplatePDF IS NOT NULL
        """
        df = pd.read_sql(query, conn)
    finally:
        conn.close()
        
    # Carrega as configurações de templates para identificar os fornecedores
    with open("config/templates.json", "r", encoding="utf-8") as f:
        templates_config = json.load(f).get("templates", {})
        
    # Associa o fornecedor a cada combinação
    def get_fornecedor(tmpl):
        return templates_config.get(tmpl, {}).get("fornecedor", "DESCONHECIDO")
        
    df["Fornecedor"] = df["TemplatePDF"].apply(get_fornecedor)
    
    # Queremos selecionar pelo menos 20 lotes distintos cobrindo:
    # - CVALE, COPACOL, AGRIFIRM, LAR
    # - Pelo menos 5 extensionistas diferentes
    # - Ambos os tipos de ração (GG e CM)
    
    lotes_selecionados_dict = {}  # key: FazendaLote, value: (extensionista, tipo_racao, fornecedor)
    
    # 1. Seleciona pelo menos um lote de cada fornecedor não-CVALE (para garantir a cobertura de fabricantes)
    for forn in ["AGRIFIRM", "COPACOL", "LAR"]:
        df_forn = df[df["Fornecedor"] == forn]
        if not df_forn.empty:
            chosen = df_forn.sample(n=1, random_state=42).iloc[0]
            lotes_selecionados_dict[chosen["FazendaLote"]] = (chosen["Extensionista"], chosen["TipoRacao"], chosen["Fornecedor"])
            
    # 2. Seleciona lotes CVALE (buscando dar preferência a lotes com ciclo completo ou GG/CM)
    df_cvale = df[df["Fornecedor"] == "CVALE"]
    
    # Para garantir GG no teste
    df_cvale_gg = df_cvale[df_cvale["TipoRacao"] == "GG"]
    if not df_cvale_gg.empty:
        for _, r in df_cvale_gg.head(5).iterrows():
            lotes_selecionados_dict[r["FazendaLote"]] = (r["Extensionista"], r["TipoRacao"], r["Fornecedor"])
            
    # Preenche com mais lotes CVALE para termos candidatos suficientes de extensionistas
    for _, r in df_cvale.iterrows():
        if len(lotes_selecionados_dict) >= 30: # Pegamos um pool inicial maior para filtrar depois
            break
        lotes_selecionados_dict[r["FazendaLote"]] = (r["Extensionista"], r["TipoRacao"], r["Fornecedor"])
        
    # 3. Agora filtramos ou selecionamos do pool para garantir as restrições:
    # - Exatamente 20 lotes
    # - Pelo menos 5 extensionistas distintos
    # - Cobrir todos os fornecedores coletados (AGRIFIRM, COPACOL, LAR, CVALE)
    # - Cobrir GG e CM
    
    final_selection = []
    
    # Primeiro, forçar a inclusão das chaves que cobrem os fornecedores raros (AGRIFIRM, COPACOL, LAR)
    raros = [k for k, v in lotes_selecionados_dict.items() if v[2] in ["AGRIFIRM", "COPACOL", "LAR"]]
    for k in raros:
        final_selection.append((lotes_selecionados_dict[k][0], lotes_selecionados_dict[k][1], k))
        
    # Adicionar outros para garantir pelo menos 5 extensionistas distintos
    pool_restante = [
        (v[0], v[1], k) for k, v in lotes_selecionados_dict.items()
        if k not in raros
    ]
    
    # Adiciona do pool de forma a maximizar a diversidade de extensionistas até termos pelo menos 5 extensionistas
    while len(final_selection) < 20 and pool_restante:
        current_exts = {item[0] for item in final_selection}
        if len(current_exts) < 5:
            # Procura no pool um extensionista que ainda não está na seleção
            for item in pool_restante:
                if item[0] not in current_exts:
                    final_selection.append(item)
                    pool_restante.remove(item)
                    break
            else:
                # Se não houver novos extensionistas, adiciona qualquer um
                final_selection.append(pool_restante.pop(0))
        else:
            final_selection.append(pool_restante.pop(0))
            
    # Se ainda faltar para completar 20, pegamos qualquer um do banco
    if len(final_selection) < 20:
        raise ValueError("Dados insuficientes no banco para selecionar 20 lotes sob as restrições.")
        
    # Mantém apenas os primeiros 20 selecionados para o teste
    lotes_selecionados = final_selection[:20]
    
    # Validações sobre a seleção efetuada
    lotes_nomes = [r[2] for r in lotes_selecionados]
    extensionistas = {r[0] for r in lotes_selecionados}
    tipos_racao = {r[1] for r in lotes_selecionados}
    fornecedores = set()
    for r in lotes_selecionados:
        lote_templates = df[df["FazendaLote"] == r[2]]["TemplatePDF"].unique()
        for t in lote_templates:
            fornecedores.add(templates_config.get(t, {}).get("fornecedor", "DESCONHECIDO"))
    
    assert len(lotes_selecionados) == 20, f"Deveriam ser selecionados exatamente 20 lotes. Selecionados: {len(lotes_selecionados)}"
    assert len(set(lotes_nomes)) == 20, "Os 20 lotes selecionados devem ser distintos."
    assert len(extensionistas) >= 5, f"Deveria haver pelo menos 5 extensionistas na seleção. Encontrado: {len(extensionistas)} ({extensionistas})"
    assert len(tipos_racao) == 2, f"Deveriam ser contemplados os 2 tipos de ração (GG e CM). Encontrado: {tipos_racao}"
    assert "AGRIFIRM" in fornecedores, "Deveria haver pelo menos um lote da AGRIFIRM."
    assert "COPACOL" in fornecedores, "Deveria haver pelo menos um lote da COPACOL."
    assert "LAR" in fornecedores, "Deveria haver pelo menos um lote da LAR."
    assert "CVALE" in fornecedores, "Deveria haver pelo menos um lote da CVALE."
    
    print("\n--- Lotes selecionados para o teste ampliado ---")
    for idx, lote_info in enumerate(lotes_selecionados):
        lote_templates = df[df["FazendaLote"] == lote_info[2]]["TemplatePDF"].unique()
        lote_forns = {templates_config.get(t, {}).get("fornecedor", "DESCONHECIDO") for t in lote_templates}
        forns_str = ", ".join(lote_forns)
        print(f"Lote {idx+1:<2}: Extensionista: {lote_info[0]:<25} | Tipo: {lote_info[1]:<2} | Fornecedor(es): {forns_str:<20} | FazendaLote: {lote_info[2]}")
    
    # 4. Para cada um dos lotes selecionados, busca todas as entregas e gera os PDFs
    writer = PDFLabelWriter()
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        for extensionista, tipo_racao, fazenda_lote in lotes_selecionados:
            # Busca todas as entregas do lote específico
            query_entregas = """
                SELECT * FROM EntregasRacao 
                WHERE FazendaLote = ?
            """
            df_entregas = pd.read_sql(query_entregas, conn, params=(fazenda_lote,))
            num_cargas = len(df_entregas)
            assert num_cargas > 0, f"Nenhuma carga encontrada no banco para o lote {fazenda_lote}"
            
            # Filtra registros ativos que devem gerar rótulo
            df_ativas = df_entregas[df_entregas['id_rotulo'].notna()].copy()
            num_rotulos_ativos = len(df_ativas)
            
            print(f"Gerando {num_rotulos_ativos} rótulos (de {num_cargas} transações) para o lote {fazenda_lote}...")
            
            # Para cada entrega ativa do lote, gera o PDF no diretório temporário
            for _, row in df_ativas.iterrows():
                id_rotulo = row['id_rotulo']
                template = row['TemplatePDF']
                data_fab = row['Data']
                lote_num = row['Lote']
                
                ext_folder = sanitize_folder_name(row['Extensionista'])
                tipo_folder = "GlobalGap" if row['TipoRacao'] == "GG" else "Comum"
                fazenda_folder = sanitize_folder_name(row['NomeFazenda'])
                lote_composto_folder = sanitize_folder_name(row['FazendaLote'])
                
                # Monta o caminho do arquivo PDF no diretório temporário
                relative_dir = os.path.join(ext_folder, tipo_folder, fazenda_folder, lote_composto_folder)
                target_dir = tmp_path / relative_dir
                pdf_filename = f"{id_rotulo}.pdf"
                output_path = target_dir / pdf_filename
                
                # Executa a escrita no PDF
                writer.write_label(
                    template_name=template,
                    data_fabricacao_raw=data_fab,
                    lote=lote_num,
                    shelf_life_days=60,
                    output_path=str(output_path)
                )
                
                # Valida se o arquivo PDF de fato existe e tem tamanho maior que zero
                assert os.path.exists(output_path), f"Arquivo PDF não foi gerado em: {output_path}"
                assert os.path.getsize(output_path) > 0, f"O arquivo PDF gerado está vazio: {output_path}"
                
            # Valida se a quantidade de arquivos PDF gerados para este lote no diretório temporário 
            # corresponde à quantidade de rótulos ativos calculada no ETL
            target_dir_lote = tmp_path / sanitize_folder_name(extensionista) / ("GlobalGap" if tipo_racao == "GG" else "Comum") / sanitize_folder_name(df_entregas.iloc[0]['NomeFazenda']) / sanitize_folder_name(fazenda_lote)
            files_in_dir = os.listdir(target_dir_lote)
            pdf_files = [f for f in files_in_dir if f.endswith('.pdf')]
            
            assert len(pdf_files) == num_rotulos_ativos, f"Deveria ter gerado {num_rotulos_ativos} PDFs para o lote {fazenda_lote}, mas gerou {len(pdf_files)}"
            
            # Valida se a ordenação alfabética no sistema de arquivos coincide com a ordenação cronológica das cargas ativas
            pdf_files_sorted = sorted(pdf_files)
            df_ativas_sorted = df_ativas.sort_values(by=['Data', 'HoraTransacao', 'id_rotulo']).reset_index(drop=True)
            expected_pdf_files = [f"{row['id_rotulo']}.pdf" for _, row in df_ativas_sorted.iterrows()]
            
            assert pdf_files_sorted == expected_pdf_files, (
                f"A ordenação alfabética dos PDFs no sistema de arquivos não bate com a cronológica.\n"
                f"Obtido: {pdf_files_sorted}\nEsperado: {expected_pdf_files}"
            )
            
            # Instancia o generator e grava o sumário .txt no diretório temporário
            generator = BatchGenerator(db_path=DATABASE_PATH, export_dir=str(tmp_path))
            sumario_path = target_dir_lote / "sumario_entregas.txt"
            generator._write_sumario(df_entregas, str(sumario_path))
            
            # Valida se o arquivo sumario_entregas.txt foi gerado e possui conteúdo
            assert os.path.exists(sumario_path), f"Arquivo sumario_entregas.txt não foi gerado em: {sumario_path}"
            assert os.path.getsize(sumario_path) > 0, f"O arquivo sumario_entregas.txt está vazio: {sumario_path}"
            
            with open(sumario_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "SUMÁRIO DE TRANSAÇÕES DE RAÇÃO" in content
                assert "BALANÇO CONSOLIDADO DO LOTE" in content
                assert "CONSUMO LÍQUIDO POR FASE DE RAÇÃO" in content
            
            print(f"Sucesso: {len(pdf_files)} PDFs e sumario_entregas.txt gerados, validados e ordenados para o lote {fazenda_lote}.")
    finally:
        conn.close()
