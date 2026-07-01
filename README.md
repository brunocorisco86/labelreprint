# 🖨️ Reimpressão Retroativa de Rótulos de Ração - C.Vale

Este projeto foi desenvolvido para automatizar a geração e reimpressão de rótulos de rações de forma retroativa para a C.Vale e seus terceiros integrados. O sistema processa dados históricos de entregas de ração, faz o enriquecimento com dados cadastrais de fazendas e regiões, e desenha dinamicamente as informações do lote nos arquivos PDF de modelo (templates) correspondentes.

O pipeline final consolidado gera apenas um **PDF mesclado unificado** (comprimido para economia de armazenamento) e um **Sumário Geral de Auditoria** por lote, eliminando a poluição visual de PDFs avulsos de cargas e facilitando o trabalho de impressão do operador.

---

## 🛠️ Tutorial: Como Executar o Sistema de Ponta a Ponta

Siga o roteiro passo a passo abaixo para configurar as dependências, organizar as fontes de entrada e rodar o pipeline completo.

### 📋 1. Pré-requisitos e Instalação do Ambiente

1.  **Clone o repositório** e entre na pasta do projeto.
2.  **Crie e ative um ambiente virtual** do Python 3.11+:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Instale as dependências** do projeto (incluindo o motor `pypdf 6.x` otimizado para desduplicação):
    ```bash
    pip install -r requirements.txt
    ```

---

### 📥 2. Organização dos Arquivos de Entrada (Raw Data e Templates)

Para que o pipeline funcione de ponta a ponta, certifique-se de que os seguintes arquivos estejam posicionados no disco:

1.  **Planilhas de Dados (raw):** Coloque-as exatamente nos seguintes caminhos dentro do projeto:
    *   `data/raw/EntregasMtech.xlsx` (Histórico de transações brutas de entregas)
    *   `data/raw/Fazendas.xlsx` (Cadastro de parceiros do SAP)
    *   `data/raw/Regioes.xlsx` (Cadastro geográfico e operacional de extensionistas)
    *   `data/raw/FiltroLotesAtivos/FiltroLotesAtivos.xlsx` (Planilha contendo os Lotes e Status operacionais que determinam a filtragem do ETL)
2.  **PDFs de Templates Físicos:** Coloque todos os PDFs limpos fornecidos pela C.Vale e parceiras no diretório:
    *   `assets/RotulosTemplate/` (Ex: `CVALE_5_ABATE_CM.pdf`, `COPACOL_4_CRESCIMENTO_CM.pdf`, `LAR_4_CRESCIMENTO_CM.pdf`, etc.)

---

### 📏 3. Ajuste e Calibração de Coordenadas (Se necessário)

Se você adicionou novos templates ou precisa recalibrar as coordenadas onde os textos são desenhados (Fabricação, Validade, Lote):

1.  **Gere as Grades de Alinhamento:**
    ```bash
    venv/bin/python3 scripts/generate_all_grids.py
    ```
    Isso gerará cópias dos PDFs de templates com uma grade de eixos milimetrada em [docs/grids/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/docs/grids).
2.  **Mapeie Coordenadas:** Abra o PDF correspondente em um visualizador. O canto superior esquerdo é o ponto **`(X=0, Y=0)`**. Leia os valores de `X` e `Y` onde o texto deve ser posicionado.
3.  **Altere no JSON:** Insira as coordenadas diretamente em [config/templates.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/templates.json) na chave do respectivo template. O conversor do preenchedor converterá as dimensões automaticamente.

---

### 🚀 4. Executando o Pipeline de Ponta a Ponta

Criamos um script orquestrador centralizado que executa de forma sequencial, limpa e com verbosidade detalhada todo o fluxo operacional do projeto.

Para rodar todo o sistema do início ao fim (sincronizar templates, gerar grades, processar ETL/MER e gerar os PDFs consolidados de produção), execute:

```bash
# Executa a geração completa de todos os lotes e tipos
venv/bin/python3 scripts/run_pipeline_ponta_a_ponta.py
```

#### 🔀 Opções de Execução Segmentada (Filtro por Tipo de Ração)
Caso necessite priorizar o lote de impressão física ou processar lotes separadamente, utilize o parâmetro `--tipo`:

*   **Apenas Rótulos GlobalGap (Exclusivos C.Vale):**
    ```bash
    venv/bin/python3 scripts/run_pipeline_ponta_a_ponta.py --tipo GG
    ```
*   **Apenas Rótulos Comuns (Terceiros e C.Vale não-GG):**
    ```bash
    venv/bin/python3 scripts/run_pipeline_ponta_a_ponta.py --tipo CM
    ```

#### O que o script mestre realiza automaticamente:
1.  **Sincronização de Metadados:** Alinha os arquivos [templates.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/templates.json) e [template_resolver.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/template_resolver.json) com o estado físico de templates no disco.
2.  **Calibração de Layouts:** Atualiza todos os arquivos com grades milimetradas em `/docs/grids` para fins de manutenção posterior.
3.  **Materialização da MER & ETL:** Lê e filtra as planilhas, monta e popula a arquitetura relacional em estrela na base SQLite (`data/processed/entregas_processadas.db`).
4.  **Geração Retroativa:** Gera e escreve as informações nos PDFs de cargas, cria os arquivos unificados condensados de produção (eliminando duplicidades operacionais, devoluções e aplicando compressão de imagens de ~46.5%), escreve os arquivos de sumários TXT e remove os PDFs de cargas intermediárias.
5.  **Logs Consolidados:** Escreve um log unificado em [pipeline_ponta_a_ponta.log](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/logs/pipeline_ponta_a_ponta.log).


---

## 📂 Organização do Repositório

*   **[scripts/run_pipeline_ponta_a_ponta.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/scripts/run_pipeline_ponta_a_ponta.py)**: Script orquestrador mestre.
*   **[src/core/data_manager.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/src/core/data_manager.py)**: Engine de ETL e ingestão para o SQLite.
*   **[src/core/generator.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/src/core/generator.py)**: Engine de geração em lote, sumários e mesclagem compactada de PDFs.
*   **[src/pdf/writer.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/src/pdf/writer.py)**: Engine geométrica de preenchimento textual no PDF original (ReportLab).
*   **[config/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config)**: Configurações de campos ([templates.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/templates.json)), fallbacks ([template_resolver.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/template_resolver.json)) e validades padrão ([shelf_life.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/shelf_life.json)).
*   **[docs/mer.md](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/docs/mer.md)**: Diagrama lógico e especificação física do modelo de dados (Star Schema).
