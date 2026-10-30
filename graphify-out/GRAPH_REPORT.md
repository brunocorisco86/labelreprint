# Graph Report - labelreprint  (2026-10-30)

## Corpus Check
- 45 files · ~36,554 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 221 nodes · 313 edges · 33 communities (14 shown, 8 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 21 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `adc4fb75`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Web Server & Email System
- Label PDF Generator & Testing
- ETL & Data Management
- Pipeline Orchestration & Grids
- Documentation & System Architecture
- Feed Label Templates & Statistics
- CI/CD & Deployment Monitoring
- Business Logic & Regulations
- CVALE/LAR Templates & Chemical Safety
- Nucleo-wise Label Generation
- Production Logs & LoggerWriter
- Web UI & Branding Assets
- API Integration Testing
- Manual Label Emitting CLI
- PDF Coordinates & Date Calculation
- Changelog & PDF Compression
- CVALE Corporate Brand Identity
- Production Keepalive Service
- Production Watchdog Service
- Data Deploy CLI
- Production Server Provisioning
- Python Dependencies Configuration

## God Nodes (most connected - your core abstractions)
1. `BatchGenerator` - 23 edges
2. `PDFLabelWriter` - 21 edges
3. `DataManager` - 19 edges
4. `sanitize_folder_name()` - 10 edges
5. `EmailSender` - 8 edges
6. `Relatório de Estatísticas Descritivas` - 8 edges
7. `LoggerWriter` - 6 edges
8. `LoggerWriter` - 6 edges
9. `main()` - 6 edges
10. `_is_na()` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Validação de Recolhas e Sobras de Ração` --semantically_similar_to--> `Detecção de Sobras do Lote Anterior`  [INFERRED] [semantically similar]
  .agents/AGENTS.md → knowledge/regras_negocio.md
- `Relatório de Estatísticas Descritivas` --references--> `AGRIFIRM 4 Crescimento CM (Template PDF)`  [EXTRACTED]
  docs/estatisticas_descritivas.md → assets/RotulosTemplate/AGRIFIRM_4_CRESCIMENTO_CM.pdf
- `Relatório de Estatísticas Descritivas` --references--> `COAMO 4 Crescimento CM (Template PDF)`  [EXTRACTED]
  docs/estatisticas_descritivas.md → assets/RotulosTemplate/COAMO_4_CRESCIMENTO_CM.pdf
- `Relatório de Estatísticas Descritivas` --references--> `COPACOL 4 Crescimento CM (Template PDF)`  [EXTRACTED]
  docs/estatisticas_descritivas.md → assets/RotulosTemplate/COPACOL_4_CRESCIMENTO_CM.pdf
- `Relatório de Estatísticas Descritivas` --references--> `CVALE 1 Pré-Inicial CM (Template PDF)`  [EXTRACTED]
  docs/estatisticas_descritivas.md → assets/RotulosTemplate/CVALE_1_PREINICIAL_CM.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **System Monitoring and Watchdog Services** — _agents_cicd_manutencao_monitoramento, cron_example_watchdog, cron_example_keepalive [INFERRED 0.85]
- **ETL and Data Cleaning Business Logic** — agents_agents_agents_validacao_recolhas_sobras, agents_agents_agents_desduplicacao_normalizacao_omissao, knowledge_regras_negocio_detecao_sobras [INFERRED 0.95]
- **PDF Generation and Compression Architecture** — _agents_skills_reimpressao_rotulos_skill_arquitetura_solucao, _agents_skills_reimpressao_rotulos_skill_eixo_y_invertido, changelog_compress_identical_objects [INFERRED 0.85]
- **CVALE Feed Templates (Chunk 2)** — home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_3_inicial2_cm_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_3_inicial2_gg_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_4_crescimento_cm_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_4_crescimento_gg_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_5_abate_cm_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_5_abate_gg_pdf [INFERRED 0.85]
- **Fase 4 Crescimento Templates** — home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_4_crescimento_cm_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_cvale_4_crescimento_gg_pdf, home_brunoconter_documentos_1_c_vale_2_projetos_10_reimpressao_rotulos_assets_rotulostemplate_lar_4_crescimento_cm_pdf [INFERRED 0.85]

## Communities (33 total, 8 thin omitted)

### Community 0 - "Web Server & Email System"
Cohesion: 0.09
Nodes (33): route, EmailSender, Classe responsável por estruturar e enviar e-mails de notificação contendo os…, Envia o relatório de sumário de entregas do lote composto por e-mail., Envia o rótulo PDF ou ZIP gerado para o e-mail informado., ai_generate_label(), ai_generate_nucleo(), ai_get_sumario() (+25 more)

### Community 1 - "Label PDF Generator & Testing"
Cohesion: 0.12
Nodes (19): main(), load_options(), load_shelf_life(), main(), main(), BatchGenerator, _is_na(), Gera um arquivo de texto resumindo as entregas, retornos, sobras e… (+11 more)

### Community 2 - "ETL & Data Management"
Cohesion: 0.11
Nodes (14): DataManager, _is_na(), Identifica a fábrica produtora da ração com base nas observações de frete, Seleciona o arquivo de template PDF com base na fábrica, fase e tipo de ração…, Executa todo o pipeline de ETL e salva os dados no SQLite, Verifica se um valor é nulo/NaN sem depender de pandas no escopo global., Classe responsável por processar os dados brutos de entregas, fazendas e…, Inicializa a tabela DestinatariosSalvos no SQLite para armazenar e-mails de… (+6 more)

### Community 3 - "Pipeline Orchestration & Grids"
Cohesion: 0.18
Nodes (10): generate_grid_overlay(), process_all_templates(), Gera um PDF em memória com uma grade de coordenadas X e Y nas dimensões…, Varre a pasta de templates e cria os PDFs de grade correspondentes., LoggerWriter, main(), Wrapper para redirecionar o stdout/stderr para o console e o arquivo de log ao…, parse_template_name() (+2 more)

### Community 4 - "Documentation & System Architecture"
Cohesion: 0.20
Nodes (12): Arquitetura da Solução de Impressão, Sistema de Eixo Y Invertido, Orientação Nativa e Rotação de Página, Skill de Impressão de Rótulos de Ração, Modelo Entidade-Relacionamento, Arquitetura Star Schema, Campos do Rótulo, Portal de Impressão de Rótulos - Rascunho de Ideias (+4 more)

### Community 5 - "Feed Label Templates & Statistics"
Cohesion: 0.20
Nodes (10): AGRIFIRM 4 Crescimento CM (Template PDF), COAMO 4 Crescimento CM (Template PDF), COPACOL 4 Crescimento CM (Template PDF), CVALE 1 Pré-Inicial CM (Template PDF), CVALE 1 Pré-Inicial GG (Template PDF), CVALE 2 Inicial 1 CM (Template PDF), CVALE 2 Inicial 1 GG (Template PDF), Relatório de Estatísticas Descritivas (+2 more)

### Community 6 - "CI/CD & Deployment Monitoring"
Cohesion: 0.29
Nodes (8): Ambiente de Desenvolvimento Local, Diretrizes de CI/CD e Ambientes, Comissionamento do Raspberry Pi, Manutenção e Monitoramento via Cron, Processo de Deploy e Atualização, Configuração do Cron na Produção, Keepalive Daemon, Watchdog Daemon

### Community 7 - "Business Logic & Regulations"
Cohesion: 0.25
Nodes (8): Diretrizes Operacionais e Regras de Negócio, Desduplicação, Normalização e Omissão no ETL, Lote de Ração Impresso, parseSumarioToWhatsApp, Sinonímia de Certificações (Global Gap / Global SLP), Validação de Recolhas e Sobras de Ração, Detecção de Sobras do Lote Anterior, Regras de Negócio de Remessa e Retorno

### Community 8 - "CVALE/LAR Templates & Chemical Safety"
Cohesion: 0.33
Nodes (3): Restrição de Ionóforos, Lar Cooperativa Agroindustrial, Narasina

### Community 9 - "Nucleo-wise Label Generation"
Cohesion: 0.70
Nodes (4): get_entregas_count(), get_lotes_by_nucleo(), get_nucleos(), main()

### Community 10 - "Production Logs & LoggerWriter"
Cohesion: 0.33
Nodes (3): LoggerWriter, main(), Wrapper para redirecionar o stdout/stderr para o console e o arquivo de log ao…

### Community 11 - "Web UI & Branding Assets"
Cohesion: 0.50
Nodes (4): C.Vale Branding System, C.Vale Logo Image, Interface do Portal (HTML), Interface em Três Abas

### Community 15 - "Changelog & PDF Compression"
Cohesion: 0.67
Nodes (3): Changelog do Projeto, Deduplicação e Compressão Física de PDFs, Rebranding Geral da Solução

### Community 16 - "CVALE Corporate Brand Identity"
Cohesion: 1.00
Nodes (3): C.Vale Brand Identity, C.Vale Logo Image, C.Vale Visual Identity Concept

## Knowledge Gaps
- **31 isolated node(s):** `deploy_data.sh script`, `setup_alpine.sh script`, `graphify`, `Workflow: graphify`, `Desduplicação, Normalização e Omissão no ETL` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 101 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BatchGenerator` connect `Label PDF Generator & Testing` to `Web Server & Email System`, `Nucleo-wise Label Generation`, `Production Logs & LoggerWriter`, `Pipeline Orchestration & Grids`?**
  _High betweenness centrality (0.136) - this node is a cross-community bridge._
- **Why does `DataManager` connect `ETL & Data Management` to `Web Server & Email System`, `Pipeline Orchestration & Grids`?**
  _High betweenness centrality (0.131) - this node is a cross-community bridge._
- **Why does `PDFLabelWriter` connect `Label PDF Generator & Testing` to `Web Server & Email System`?**
  _High betweenness centrality (0.076) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `BatchGenerator` (e.g. with `PDFLabelWriter` and `ai_generate_nucleo()`) actually correct?**
  _`BatchGenerator` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `PDFLabelWriter` (e.g. with `BatchGenerator` and `ai_generate_label()`) actually correct?**
  _`PDFLabelWriter` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `deploy_data.sh script`, `setup_alpine.sh script`, `graphify` to the rest of the system?**
  _31 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Web Server & Email System` be split into smaller, more focused modules?**
  _Cohesion score 0.09102564102564102 - nodes in this community are weakly interconnected._