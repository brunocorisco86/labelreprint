# Graph Report - .  (2026-07-10)

## Corpus Check
- Corpus is ~34,650 words - fits in a single context window. You may not need a graph.

## Summary
- 195 nodes · 254 edges · 33 communities (26 shown, 7 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

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
1. `BatchGenerator` - 24 edges
2. `PDFLabelWriter` - 20 edges
3. `DataManager` - 13 edges
4. `sanitize_folder_name()` - 10 edges
5. `LoggerWriter` - 8 edges
6. `EmailSender` - 8 edges
7. `Relatório de Estatísticas Descritivas` - 8 edges
8. `LoggerWriter` - 7 edges
9. `main()` - 6 edges
10. `process_all_templates()` - 5 edges

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

## Communities (33 total, 7 thin omitted)

### Community 0 - "Web Server & Email System"
Cohesion: 0.09
Nodes (14): EmailSender, Classe responsável por estruturar e enviar e-mails de notificação     contendo o, Envia o relatório de sumário de entregas do lote composto por e-mail., Envia o rótulo PDF ou ZIP gerado para o e-mail informado., generate_label(), generate_nucleo_labels(), get_emails(), get_templates() (+6 more)

### Community 1 - "Label PDF Generator & Testing"
Cohesion: 0.16
Nodes (14): main(), main(), main(), BatchGenerator, Sanitiza strings para nomes de pastas seguros no Linux:     Remove acentos, cara, Gera um arquivo de texto resumindo as entregas, retornos, sobras e transferência, Classe responsável por coordenar a geração em lote de rótulos retroativos     a, Mescla todos os PDFs de rótulos ativos de um lote em um único PDF         no for (+6 more)

### Community 2 - "ETL & Data Management"
Cohesion: 0.13
Nodes (8): DataManager, Seleciona o arquivo de template PDF com base na fábrica, fase e tipo de ração (C, Executa todo o pipeline de ETL e salva os dados no SQLite, Classe responsável por processar os dados brutos de entregas, fazendas e regiões, Normaliza a string FazendaLote para remover zeros à esquerda do lote e garantir, Extrai o lote ordinal da string FazendaLote (ex: '1351-1' -> '01'), Mapeia o nome da fórmula para a fase da ração correspondente, Identifica a fábrica produtora da ração com base nas observações de frete

### Community 3 - "Pipeline Orchestration & Grids"
Cohesion: 0.19
Nodes (10): generate_grid_overlay(), process_all_templates(), Gera um PDF em memória com uma grade de coordenadas X e Y     nas dimensões espe, Varre a pasta de templates e cria os PDFs de grade correspondentes., LoggerWriter, main(), Wrapper para redirecionar o stdout/stderr para o console e o arquivo de log ao m, parse_template_name() (+2 more)

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

### Community 11 - "Web UI & Branding Assets"
Cohesion: 0.40
Nodes (5): favicon(), C.Vale Branding System, C.Vale Logo Image, Interface do Portal (HTML), Interface em Três Abas

### Community 13 - "Manual Label Emitting CLI"
Cohesion: 0.83
Nodes (3): load_options(), load_shelf_life(), main()

### Community 15 - "Changelog & PDF Compression"
Cohesion: 0.67
Nodes (3): Changelog do Projeto, Deduplicação e Compressão Física de PDFs, Rebranding Geral da Solução

### Community 16 - "CVALE Corporate Brand Identity"
Cohesion: 1.00
Nodes (3): C.Vale Brand Identity, C.Vale Logo Image, C.Vale Visual Identity Concept

## Knowledge Gaps
- **29 isolated node(s):** `deploy_data.sh script`, `setup_alpine.sh script`, `Desduplicação, Normalização e Omissão no ETL`, `Lote de Ração Impresso`, `Sinonímia de Certificações (Global Gap / Global SLP)` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `BatchGenerator` connect `Label PDF Generator & Testing` to `Web Server & Email System`, `Nucleo-wise Label Generation`, `Production Logs & LoggerWriter`, `Pipeline Orchestration & Grids`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `DataManager` connect `ETL & Data Management` to `Pipeline Orchestration & Grids`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `PDFLabelWriter` connect `Label PDF Generator & Testing` to `Web Server & Email System`, `Manual Label Emitting CLI`, `PDF Coordinates & Date Calculation`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `BatchGenerator` (e.g. with `LoggerWriter` and `LoggerWriter`) actually correct?**
  _`BatchGenerator` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `LoggerWriter` (e.g. with `DataManager` and `BatchGenerator`) actually correct?**
  _`LoggerWriter` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Gera um PDF em memória com uma grade de coordenadas X e Y     nas dimensões espe`, `Varre a pasta de templates e cria os PDFs de grade correspondentes.`, `Wrapper para redirecionar o stdout/stderr para o console e o arquivo de log ao m` to the rest of the system?**
  _57 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Web Server & Email System` be split into smaller, more focused modules?**
  _Cohesion score 0.09359605911330049 - nodes in this community are weakly interconnected._