import sqlite3
import pandas as pd
import os

DATABASE_PATH = "data/processed/entregas_processadas.db"
OUTPUT_PATH = "docs/estatisticas_descritivas.md"

def generate_stats():
    if not os.path.exists(DATABASE_PATH):
        print(f"Erro: Banco de dados {DATABASE_PATH} não encontrado!")
        return
        
    conn = sqlite3.connect(DATABASE_PATH)
    
    # 1. Carrega todas as entregas
    df = pd.read_sql("SELECT * FROM EntregasRacao", conn)
    
    # 2. Carrega Cadastro de Fazendas
    df_fazendas = pd.read_sql("SELECT * FROM Fazendas", conn)
    
    # 3. Carrega Regiões
    df_regioes = pd.read_sql("SELECT * FROM Regioes", conn)
    
    # Gera estatísticas
    total_entregas = len(df)
    total_fazendas = df['Fazenda'].nunique()
    total_lotes = df['FazendaLote'].nunique()
    
    # Distribuição por Tipo de Ração (GlobalGap vs Comum)
    tipo_dist = df['TipoRacao'].value_counts()
    tipo_dist_pct = df['TipoRacao'].value_counts(normalize=True) * 100
    
    # Distribuição por Fábrica de Ração
    fabrica_dist = df['FabricaRacao'].value_counts()
    fabrica_dist_pct = df['FabricaRacao'].value_counts(normalize=True) * 100
    
    # Distribuição por Fase da Ração
    fase_dist = df['FaseRacao'].value_counts()
    fase_dist_pct = df['FaseRacao'].value_counts(normalize=True) * 100
    
    # Distribuição por Extensionista (Top 10)
    ext_dist = df['Extensionista'].value_counts().head(15)
    
    # Quantidade média e total entregue por entrega
    qtd_total = df['QuantidadeEntregue'].sum()
    qtd_media = df['QuantidadeEntregue'].mean()
    
    # Monta o markdown
    md_content = f"""# Relatório de Estatísticas Descritivas

Este relatório descreve estatísticas gerais sobre os dados de entregas de ração processados na base de dados histórica (maio e junho).

---

## 📊 Métricas Gerais

| Métrica | Valor |
| :--- | :---: |
| **Total de Entregas Registradas** | {total_entregas:,} |
| **Total de Aviários/Fazendas Distintos** | {total_fazendas:,} |
| **Total de Lotes Distintos (AviarioLote)** | {total_lotes:,} |
| **Quantidade Total Entregue** | {qtd_total:,.2f} kg |
| **Média por Entrega** | {qtd_media:,.2f} kg |

---

## 🌾 Distribuição por Tipo de Ração

| Tipo de Ração | Descrição | Quantidade | Percentual |
| :--- | :--- | :---: | :---: |
| **CM** | Comum | {tipo_dist.get('CM', 0):,} | {tipo_dist_pct.get('CM', 0.0):.2f}% |
| **GG** | GlobalGap (Certificado) | {tipo_dist.get('GG', 0):,} | {tipo_dist_pct.get('GG', 0.0):.2f}% |

---

## 🏭 Distribuição por Fábrica de Ração (Origem)

A origem da ração é inferida com base nos registros do frete.

| Fábrica | Quantidade de Entregas | Percentual |
| :--- | :---: | :---: |
"""
    for fab in fabrica_dist.index:
        md_content += f"| **{fab}** | {fabrica_dist[fab]:,} | {fabrica_dist_pct[fab]:.2f}% |\n"
        
    md_content += """
---

## 🔄 Distribuição por Fase de Ração

Fase mapeada a partir do nome da fórmula de ração.

| Fase | Quantidade | Percentual |
| :--- | :---: | :---: |
"""
    for fase in fase_dist.index:
        md_content += f"| **{fase}** | {fase_dist[fase]:,} | {fase_dist_pct[fase]:.2f}% |\n"

    md_content += """
---

## 🧑‍⚕️ Entregas por Extensionista (Top 15)

O Extensionista nominal é integrado a partir das informações de regiões.

| Extensionista | Quantidade de Entregas | Percentual |
| :--- | :---: | :---: |
"""
    for ext in ext_dist.index:
        pct = (ext_dist[ext] / total_entregas) * 100
        md_content += f"| {ext} | {ext_dist[ext]:,} | {pct:.2f}% |\n"

    md_content += """
---

## 📁 Detalhamento de Templates Usados

Modelos de rótulo PDF associados aos registros.

| Template PDF | Quantidade | Percentual |
| :--- | :---: | :---: |
"""
    template_dist = df['TemplatePDF'].value_counts()
    template_dist_pct = df['TemplatePDF'].value_counts(normalize=True) * 100
    for tmpl in template_dist.index:
        md_content += f"| `{tmpl}` | {template_dist[tmpl]:,} | {template_dist_pct[tmpl]:.2f}% |\n"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    print(f"[Stats] Relatório de estatísticas descritivas gerado com sucesso em: {OUTPUT_PATH}")
    conn.close()

if __name__ == "__main__":
    generate_stats()
