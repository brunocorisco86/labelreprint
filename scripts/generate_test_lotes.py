import os
import sys

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src e scripts
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import sqlite3
import random
import json
import pandas as pd
from src.core.generator import BatchGenerator, sanitize_folder_name
from src.pdf.writer import PDFLabelWriter

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/processed/entregas_processadas.db")
EXPORT_DIR = os.getenv("EXPORT_DIR", "Export")

def main():
    # 1. Verifica se o banco de dados existe
    if not os.path.exists(DATABASE_PATH):
        print(f"Erro: Banco de dados não encontrado em {DATABASE_PATH}. Execute o ETL primeiro.")
        return
    
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
    
    # 1. Seleciona pelo menos um lote de cada fornecedor não-CVALE
    for forn in ["AGRIFIRM", "COPACOL", "LAR"]:
        df_forn = df[df["Fornecedor"] == forn]
        if not df_forn.empty:
            chosen = df_forn.sample(n=1, random_state=42).iloc[0]
            lotes_selecionados_dict[chosen["FazendaLote"]] = (chosen["Extensionista"], chosen["TipoRacao"], chosen["Fornecedor"])
            
    # 2. Seleciona lotes CVALE
    df_cvale = df[df["Fornecedor"] == "CVALE"]
    
    # Para garantir GG no teste
    df_cvale_gg = df_cvale[df_cvale["TipoRacao"] == "GG"]
    if not df_cvale_gg.empty:
        for _, r in df_cvale_gg.head(5).iterrows():
            lotes_selecionados_dict[r["FazendaLote"]] = (r["Extensionista"], r["TipoRacao"], r["Fornecedor"])
            
    # Preenche com mais lotes CVALE
    for _, r in df_cvale.iterrows():
        if len(lotes_selecionados_dict) >= 30:
            break
        lotes_selecionados_dict[r["FazendaLote"]] = (r["Extensionista"], r["TipoRacao"], r["Fornecedor"])
        
    final_selection = []
    
    # Adiciona os lotes que cobrem os fornecedores raros
    raros = [k for k, v in lotes_selecionados_dict.items() if v[2] in ["AGRIFIRM", "COPACOL", "LAR"]]
    for k in raros:
        final_selection.append((lotes_selecionados_dict[k][0], lotes_selecionados_dict[k][1], k))
        
    # Adiciona outros do pool de forma a garantir pelo menos 5 extensionistas
    pool_restante = [
        (v[0], v[1], k) for k, v in lotes_selecionados_dict.items()
        if k not in raros
    ]
    
    while len(final_selection) < 20 and pool_restante:
        current_exts = {item[0] for item in final_selection}
        if len(current_exts) < 5:
            for item in pool_restante:
                if item[0] not in current_exts:
                    final_selection.append(item)
                    pool_restante.remove(item)
                    break
            else:
                final_selection.append(pool_restante.pop(0))
        else:
            final_selection.append(pool_restante.pop(0))
            
    if len(final_selection) < 20:
        print("Erro: Dados insuficientes para selecionar 20 lotes sob as restrições.")
        return
        
    lotes_selecionados = final_selection[:20]
    
    print("--- Lotes selecionados para geração física em Export/ ---")
    for idx, lote_info in enumerate(lotes_selecionados):
        lote_templates = df[df["FazendaLote"] == lote_info[2]]["TemplatePDF"].unique()
        lote_forns = {templates_config.get(t, {}).get("fornecedor", "DESCONHECIDO") for t in lote_templates}
        forns_str = ", ".join(lote_forns)
        print(f"Lote {idx+1:<2}: Extensionista: {lote_info[0]:<25} | Tipo: {lote_info[1]:<2} | Fornecedor(es): {forns_str:<20} | FazendaLote: {lote_info[2]}")
        
    # 3. Gera os PDFs das cargas diretamente na pasta Export/
    writer = PDFLabelWriter()
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        for extensionista, tipo_racao, fazenda_lote in lotes_selecionados:
            query_entregas = "SELECT * FROM EntregasRacao WHERE FazendaLote = ?"
            df_entregas = pd.read_sql(query_entregas, conn, params=(fazenda_lote,))
            num_cargas = len(df_entregas)
            
            print(f"\nProcessando Lote {fazenda_lote} ({num_cargas} cargas)...")
            
            for _, row in df_entregas.iterrows():
                id_rotulo = row['id_rotulo']
                if pd.isna(id_rotulo) or not id_rotulo:
                    continue
                template = row['TemplatePDF']
                data_fab = row['Data']
                lote_num = row['Lote']
                
                ext_folder = sanitize_folder_name(row['Extensionista'])
                tipo_folder = "GlobalGap" if row['TipoRacao'] == "GG" else "Comum"
                fazenda_folder = sanitize_folder_name(row['NomeFazenda'])
                lote_composto_folder = sanitize_folder_name(row['FazendaLote'])
                
                relative_dir = os.path.join(ext_folder, tipo_folder, fazenda_folder, lote_composto_folder)
                target_dir = os.path.join(EXPORT_DIR, relative_dir)
                pdf_filename = f"{id_rotulo}.pdf"
                output_path = os.path.join(target_dir, pdf_filename)
                
                writer.write_label(
                    template_name=template,
                    data_fabricacao_raw=data_fab,
                    lote=lote_num,
                    shelf_life_days=60,
                    output_path=output_path
                )
                
            # Gera o sumário em formato .txt e mescla os PDFs
            generator = BatchGenerator(db_path=DATABASE_PATH, export_dir=EXPORT_DIR)
            sumario_path = os.path.join(target_dir, "sumario_entregas.txt")
            generator._write_sumario(df_entregas, sumario_path)
            try:
                generator._merge_pdfs_lote(df_entregas, target_dir)
            except Exception as e:
                print(f"  [Erro] Falha ao mesclar PDFs para o lote {fazenda_lote}: {e}")
            
            print(f"-> PDFs, sumário e mescla gerados com sucesso em: {os.path.join(EXPORT_DIR, ext_folder, tipo_folder, sanitize_folder_name(df_entregas.iloc[0]['NomeFazenda']), lote_composto_folder)}")
            
        # 4. Gera a ficha catalográfica (catalogo_fornecedores.txt) na raiz da pasta Export/
        catalogo_path = os.path.join(EXPORT_DIR, "catalogo_fornecedores.txt")
        print(f"\nGerando catálogo de fornecedores em: {catalogo_path}...")
        
        catalogo_data = {}
        for extensionista, tipo_racao, fazenda_lote in lotes_selecionados:
            query_lote = "SELECT DISTINCT NomeFazenda, Extensionista, TipoRacao, TemplatePDF FROM EntregasRacao WHERE FazendaLote = ?"
            df_lote = pd.read_sql(query_lote, conn, params=(fazenda_lote,))
            for _, r in df_lote.iterrows():
                tmpl = r["TemplatePDF"]
                if pd.isna(tmpl) or not tmpl:
                    continue
                forn = templates_config.get(tmpl, {}).get("fornecedor", "DESCONHECIDO")
                
                if forn not in catalogo_data:
                    catalogo_data[forn] = {}
                
                lote_key = (fazenda_lote, r["NomeFazenda"], r["TipoRacao"], r["Extensionista"])
                catalogo_data[forn][lote_key] = True
                
        with open(catalogo_path, "w", encoding="utf-8") as f:
            f.write("================================================================================\n")
            f.write("📖 FICHA CATALOGRÁFICA: FORNECEDORES DE RAÇÃO POR LOTE / PRODUTOR\n")
            f.write("================================================================================\n\n")
            f.write("Este arquivo ajuda a localizar fisicamente os PDFs e sumários de testes gerados\n")
            f.write("com base nos fornecedores e suas respectivas fases de ração.\n\n")
            
            for forn in sorted(catalogo_data.keys()):
                f.write(f"--------------------------------------------------------------------------------\n")
                f.write(f"🏭 FORNECEDOR: {forn}\n")
                f.write(f"--------------------------------------------------------------------------------\n")
                f.write(f"{'Lote/Aviário':<15} | {'Produtor / Fazenda':<35} | {'Tipo':<5} | {'Extensionista':<20}\n")
                f.write(f"--------------------------------------------------------------------------------\n")
                
                sorted_keys = sorted(catalogo_data[forn].keys(), key=lambda x: x[0])
                for fazenda_lote, nome_fazenda, tipo, ext in sorted_keys:
                    f.write(f"{fazenda_lote:<15} | {nome_fazenda:<35} | {tipo:<5} | {ext:<20}\n")
                f.write("\n")
                
        print("-> Catálogo de fornecedores gerado com sucesso!")
        
        # 5. Gera amostras planas de cada template cadastrado no templates.json em Export/AmostrasTemplates/
        amostras_dir = os.path.join(EXPORT_DIR, "AmostrasTemplates")
        os.makedirs(amostras_dir, exist_ok=True)
        print(f"\nGerando amostras planas de templates em: {amostras_dir}...")
        
        for template_name in sorted(templates_config.keys()):
            query_sample = """
                SELECT * FROM EntregasRacao 
                WHERE TemplatePDF = ? 
                  AND id_rotulo IS NOT NULL
            """
            df_sample = pd.read_sql(query_sample, conn, params=(template_name,))
            if not df_sample.empty:
                # Escolhe um registro aleatório do banco de dados para este template
                row_sample = df_sample.sample(n=1, random_state=42).iloc[0]
                output_sample_path = os.path.join(amostras_dir, template_name)
                
                try:
                    writer.write_label(
                        template_name=template_name,
                        data_fabricacao_raw=row_sample['Data'],
                        lote=row_sample['Lote'],
                        shelf_life_days=60,
                        output_path=output_sample_path
                    )
                    print(f"  [Amostra] Gerada com sucesso: {template_name}")
                except Exception as e:
                    print(f"  [Erro] Falha ao gerar amostra para {template_name}: {e}")
                    
    finally:
        conn.close()

if __name__ == "__main__":
    main()
