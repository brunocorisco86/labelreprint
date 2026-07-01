# 📋 Changelog do Projeto - Reimpressão de Rótulos C.Vale

Este arquivo registra o histórico cronológico de todas as modificações, melhorias e refatorações realizadas no sistema de geração e reimpressão de rótulos.

---

## [1.5.0] - 2026-07-01
### Adicionado
*   **Pipeline Orquestrador Mestre (`run_pipeline_ponta_a_ponta.py`):** Criado script centralizado para execução sequencial de todas as fases (Sincronização -> Geração de Grades -> ETL/MER -> Geração de Produção).
*   **Geração Segmentada por Tipo de Ração:** Adicionado parâmetro `--tipo` (GG, CM, ALL) nos scripts de produção e pipeline para viabilizar a priorização de impressão dos rótulos exclusivos C.Vale (GlobalGap).
*   **Amostras de Dados Anonimizadas (`data/templates/`):** Criada pasta contendo os cabeçalhos (`head()`) anonimizados e mockados das planilhas reais de entrada (preservando segredos de negócio e dados confidenciais SAP).

---

## [1.4.0] - 2026-06-30
### Adicionado
*   **Suporte a Logs de Produção (`logs/geracao_producao.log`):** Criado sistema de gravação física exclusiva para diagnosticar a última execução retroativa diretamente no disco.
*   **Deduplicação e Compressão Física de PDFs (PyPDF 6.x):** Introduzido método `compress_identical_objects()` para consolidar imagens de templates duplicadas em referências únicas, reduzindo o armazenamento físico consolidado em **~46.5%**.
*   **Otimização Computacional do Merge:** Desativação de compressão de streams individuais e limitação da desduplicação complexa apenas para lotes compostos com mais de 1 rótulo (lotes de 1 rótulo são mesclados instantaneamente).

---

## [1.3.0] - 2026-06-28
### Adicionado
*   **Unificação de PDFs por Lote Composto:** Adicionado processo de mesclagem cronológica dos rótulos gerados, mantendo apenas o PDF consolidado e a ficha `sumario_entregas.txt` no diretório final de cada lote.
*   **Regra de Nomeação Dinâmica:** O PDF consolidado agora é nomeado sob o padrão `{lote}-{primeiro_nome_produtor}-{quantidade_rotulos}.pdf`.

---

## [1.2.0] - 2026-06-25
### Adicionado
*   **Mapeamento de Validades Dinâmicas (`shelf_life.json`):** Estruturado arquivo de configuração com prazos padrão de expiração diferenciados por fabricante (ex: C.Vale, Lar, Copacol, Agrifirm).
*   **Layout Invertido com Origem no Topo:** Suporte nativo ao eixo Y invertido (canto superior esquerdo) nas configurações do `templates.json`, facilitando a leitura de coordenadas geométricas em softwares de design e grades milimetradas.

---

## [1.1.0] - 2026-06-20
### Adicionado
*   **ETL em Star Schema e SQLite:** Implementada ingestão automática das planilhas raw para as tabelas fato (`EntregasRacao`) e dimensões (`Fazendas`, `Regioes`, `FiltroLotesAtivos`).
*   **Filtro de Lotes Ativos:** Inclusão lógica da tabela `FiltroLotesAtivos` do Mtech para determinar a seleção física das entregas processadas.
*   **Regras Antiduplicidade:** Implementadas travas no ETL para omitir emissão de rótulos por duplicidade diária na mesma ração e devoluções integrais de carga.

---

## [1.0.0] - 2026-06-15
### Adicionado
*   Estrutura básica do projeto, repositório Git e ambiente virtual Python.
*   Templates originais fornecidos pela C.Vale na pasta `assets/RotulosTemplate`.
