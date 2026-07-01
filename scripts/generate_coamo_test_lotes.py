import os
import sys
import sqlite3
import json
import pandas as pd

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.core.generator import BatchGenerator, sanitize_folder_name
from src.pdf.writer import PDFLabelWriter

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/processed/entregas_processadas.db")
EXPORT_DIR = os.getenv("EXPORT_DIR", "Export")

def main():
    # 1. Verifica se o banco de dados existe
    if not os.path.exists(DATABASE_PATH):
        print(f"Erro: Banco de dados não encontrado em {DATABASE_PATH}. Execute o ETL primeiro.")
        return
    
    # 2. Conecta ao banco de dados para selecionar 3 lotes com entregas da COAMO
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Busca lotes que possuem pelo menos uma entrega associada a fábrica COAMO
        query_lotes = """
            SELECT DISTINCT FazendaLote
            FROM EntregasRacao
            WHERE FabricaRacao = 'COAMO'
              AND Extensionista IS NOT NULL 
              AND TipoRacao IS NOT NULL 
              AND FazendaLote IS NOT NULL
              AND TemplatePDF IS NOT NULL
        """
        df_lotes = pd.read_sql(query_lotes, conn)
        
        if df_lotes.empty:
            print("Erro: Nenhum lote com cargas da COAMO foi encontrado no banco de dados.")
            return
        
        # Seleciona exatamente 3 lotes distintos de forma consistente
        selected_lotes = df_lotes['FazendaLote'].head(3).tolist()
        print(f"Lotes selecionados contendo cargas da COAMO: {selected_lotes}")
        print("-" * 80)
        
        # Carrega as configurações de templates
        with open("config/templates.json", "r", encoding="utf-8") as f:
            templates_config = json.load(f).get("templates", {})
            
        writer = PDFLabelWriter()
        
        for fazenda_lote in selected_lotes:
            # Obtém todas as entregas do lote
            query_entregas = "SELECT * FROM EntregasRacao WHERE FazendaLote = ?"
            df_entregas = pd.read_sql(query_entregas, conn, params=(fazenda_lote,))
            num_cargas = len(df_entregas)
            
            # Filtra apenas a entrega de COAMO para mostrar informações
            coamo_deliveries = df_entregas[df_entregas['FabricaRacao'] == 'COAMO']
            
            print(f"\nProcessando Lote {fazenda_lote} ({num_cargas} cargas no total, sendo {len(coamo_deliveries)} da COAMO)...")
            
            target_dir = None
            for _, row in df_entregas.iterrows():
                id_rotulo = row['id_rotulo']
                # Se id_rotulo for nulo, a entrega foi omitida de acordo com as regras de negócio
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
                
                os.makedirs(target_dir, exist_ok=True)
                pdf_filename = f"{id_rotulo}.pdf"
                output_path = os.path.join(target_dir, pdf_filename)
                
                # Gera o PDF individual para cada carga elegível
                writer.write_label(
                    template_name=template,
                    data_fabricacao_raw=data_fab,
                    lote=lote_num,
                    shelf_life_days=60,
                    output_path=output_path
                )
                print(f"  [PDF] Gerado: {pdf_filename} | Fábrica: {row['FabricaRacao']} -> {template}")
                
            if target_dir:
                # Gera o sumário financeiro/transacional (sumario_entregas.txt)
                sumario_path = os.path.join(target_dir, "sumario_entregas.txt")
                generator = BatchGenerator(db_path=DATABASE_PATH, export_dir=EXPORT_DIR)
                generator._write_sumario(df_entregas, sumario_path)
                print(f"  [Sumário] Gerado em: {sumario_path}")
                
                # Mescla os PDFs individuais em um único PDF do Lote
                try:
                    generator._merge_pdfs_lote(df_entregas, target_dir)
                    print(f"  [Merge] PDFs mesclados com sucesso!")
                except Exception as e:
                    print(f"  [Erro Merge] Falha ao mesclar PDFs para o lote {fazenda_lote}: {e}")
                    
                print(f"✔️ Lote {fazenda_lote} concluído em: {target_dir}")
                
    finally:
        conn.close()

if __name__ == "__main__":
    main()
