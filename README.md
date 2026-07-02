# 🖨️ Portal de Impressão de Rótulos de Ração - C.Vale

Este projeto foi desenvolvido para automatizar a geração e impressão de rótulos de rações de forma retroativa e sob demanda para a C.Vale e seus parceiros integrados. O sistema processa dados históricos de entregas de ração, faz o enriquecimento com dados cadastrais de fazendas e regiões, e desenha dinamicamente as informações do lote nos arquivos PDF de modelo (templates) correspondentes.

O portal centralizado gera apenas um **PDF mesclado unificado** (comprimido para economia de armazenamento) e um **Sumário Geral de Auditoria** por lote, facilitando o trabalho de impressão do operador.

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

### ✍️ 5. Geração e Reimpressão Manual de Rótulo Específico

Se você precisar gerar manualmente um rótulo preenchido para uma ração e um dia de fabricação específico (sem depender de dados no banco ou planilhas), você tem duas opções de execução:

#### Opção A: Pelo Portal Web Local (Recomendado)
O projeto conta com um portal local moderno e intuitivo para seleção de templates, preenchimento interativo de datas (com preview dinâmico), consulta de lotes zootécnicos e compartilhamento de relatórios.

1. **Inicie o servidor local de desenvolvimento:**
   ```bash
   PYTHONPATH=. venv/bin/python3 scripts/run_webserver.py
   ```
2. **Acesse no navegador:** Abra o endereço [http://localhost:5000](http://localhost:5000).
3. **Abas de Controle e Operação:**
   * **Aba 1 (Emissão Avulsa):** Escolha o tipo de ração/template, a data de fabricação, altere se desejar a data de validade através de um calendário interativo e gere o PDF de forma avulsa. Após gerar, você pode baixar o PDF, enviá-lo por e-mail com logotipo C.Vale embutido, ou cadastrar novos destinatários.
   * **Aba 2 (Geração Núcleo):** Selecione o núcleo de criação desejado para listar todas as granjas vinculadas e o volume de entregas. Clique em "Gerar Rótulos do Núcleo" para disparar o pipeline relacional completo de forma segmentada.
   * **Aba 3 (Consulta Lotes):** Escolha o Produtor/Aviário e o Lote Composto para renderizar a ficha do lote e o sumário consolidado diretamente na tela. O console de terminal transiciona para azul neon claro exibindo o arquivo `sumario_entregas.txt`. Nesta aba você pode copiar o sumário diagramado verticalmente para colar no WhatsApp do produtor, ou enviar a ficha por e-mail.
4. **Console de Auditoria Lateral:** O painel direito do terminal monitora logs de auditoria (`logs/geracao_manual.log`) em tempo real em verde neon ou exibe sumários ativos de lotes em azul neon claro.

---

#### Opção B: Pelo Terminal Interativo (CLI)
Uma alternativa direta via console interativo que roda em ciclo de loop sequencial.

1. **Execute o script interativo:**
   ```bash
   PYTHONPATH=. venv/bin/python3 scripts/generate_manual_label.py
   ```
2. **Escolha o tipo de ração** informando o número correspondente exibido no terminal. As opções são resolvidas a partir do arquivo [template_resolver.json](file:///home/bruno/Documentos/1_C.VALE/2%20-%20PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/config/template_resolver.json).
3. **Informe a data de fabricação** no formato `dd/mm/aaaa` (ex: `30/06/2026`).
4. **Valide as informações calculadas** apresentadas no resumo do console e opcionalmente insira uma data de validade customizada.
5. **Acesse o arquivo gerado** na pasta `Export/manuais/`.

---

#### Opção C: Geração por Núcleo de Criação (CLI)
Caso queira rodar o pipeline em lote de forma segmentada para todos os lotes que pertencem a um núcleo específico (com base nas vinculações cadastradas em `FiltroMissaoEuropa.xlsx`):

1. **Execute o script de núcleo:**
   ```bash
   PYTHONPATH=. venv/bin/python3 scripts/generate_labels_by_nucleo.py
   ```
2. **Selecione o núcleo:** O terminal exibirá todos os núcleos com lotes ativos cadastrados. Digite o número do núcleo desejado.
3. **Valide a listagem de granjas:** O script buscará todos os lotes associados, listará o nome de cada granja e o total de entregas encontradas na base SQLite.
4. **Gerar e Mesclar:** Confirme digitando **`s`**. A engine gerará os PDFs unificados e sumários compactados para todas as granjas do respectivo núcleo na pasta `Export/`.

---

## 📂 Organização do Repositório

*   **[scripts/run_pipeline_ponta_a_ponta.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/scripts/run_pipeline_ponta_a_ponta.py)**: Script orquestrador mestre.
*   **[scripts/run_webserver.py](file:///home/bruno/Documentos/1_C.VALE/2 - PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/scripts/run_webserver.py)**: Script de inicialização do portal de impressão de rótulos de ração.
*   **[scripts/generate_manual_label.py](file:///home/bruno/Documentos/1_C.VALE/2%20-%20PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/scripts/generate_manual_label.py)**: Script interativo para geração manual e pontual de rótulos via CLI.
*   **[scripts/generate_labels_by_nucleo.py](file:///home/bruno/Documentos/1_C.VALE/2%20-%20PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/scripts/generate_labels_by_nucleo.py)**: Script de geração segmentada em lote filtrada por Núcleo de Criação.
*   **[src/core/data_manager.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/src/core/data_manager.py)**: Engine de ETL e ingestão para o SQLite.
*   **[src/core/generator.py](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/src/core/generator.py)**: Engine de geração em lote, sumários e mesclagem compactada de PDFs.
*   **[src/pdf/writer.py](file:///home/bruno/Documentos/1_C.VALE/2 - PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/src/pdf/writer.py)**: Engine geométrica de preenchimento textual no PDF original (ReportLab).
*   **[config/](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config)**: Configurações de campos ([templates.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/templates.json)), fallbacks ([template_resolver.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/template_resolver.json)) e validades padrão ([shelf_life.json](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/config/shelf_life.json)).
*   **[docs/mer.md](file:///home/brunoconter/Documentos/1_C.VALE/2%20-%20PROJETOS/10_REIMPRESSAO_ROTULOS/docs/mer.md)**: Diagrama lógico e especificação física do modelo de dados (Star Schema).
