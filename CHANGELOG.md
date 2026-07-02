# 📋 Changelog do Projeto - Impressão de Rótulos de Ração C.Vale

Este arquivo registra o histórico cronológico de todas as modificações, melhorias e refatorações realizadas no sistema de geração e impressão de rótulos de ração.

---

## [2.0.0] - 2026-07-02
### Adicionado
*   **Portal de Impressão de Rótulos de Ração (UI com Abas)**: Desenvolvido portal local Flask unificado com três abas de controle: *Emissão Avulsa*, *Geração Núcleo* e *Consulta Lotes*.
*   **Aba Consulta Lotes & Sumários**: Painel interativo para pesquisar produtores e carregar o arquivo `sumario_entregas.txt` correspondente de forma dinâmica, renderizando no terminal lateral em azul neon claro.
*   **Envio de Rótulos e Sumários por E-mail**: Integração SMTP com o backend Flask (`email_sender.py`) para enviar e-mails estilizados com a paleta Azul Cobalto e Branco contendo o logotipo institucional da C.Vale inline (CID).
*   **Histórico de Destinatários de E-mail (JSON)**: Criada base de e-mails persistente em `config/destinatarios_salvos.json` contendo endereços pré-carregados (`bruno.conter@cvale.com.br` e `vinicius.duarte@cvale.com.br`) e salvando automaticamente novos e-mails digitados.
*   **Exportação Otimizada para WhatsApp (Mobile-First)**: Botão verde para copiar o sumário do lote já formatado verticalmente para colar no WhatsApp, utilizando emojis e bullet-points sem quebras de linha para visualização perfeita em qualquer celular.
*   **Utilitário de Teste de Conexão SMTP (`test_smtp.py`)**: Script interativo no console para validar conexão TCP, criptografia TLS/SSL e login de e-mail a partir do arquivo `.env`.

### Alterado
*   **Rebranding Geral da Solução**: Removido o termo "Reimpressão" para afastar a conotação de retrabalho. O sistema foi rebatizado como **Portal de Impressão de Rótulos de Ração C.Vale**. O banner do servidor, cabeçalhos, rodapés e e-mails foram redefinidos para a nova nomenclatura.
*   **Terminal de Logs com Duplo Propósito**: O console lateral de auditoria agora transiciona dinamicamente para mostrar sumários de lotes em azul neon claro, restaurando a visualização de logs em verde neon ao retornar para as abas de geração.

---

## [1.5.1] - 2026-07-01
### Corrigido
*   **Normalização de FazendaLote:** Adicionado tratamento no ETL para unificar códigos de lotes zootécnicos (removendo zeros à esquerda nos lotes, ex: `1342-05` $\rightarrow$ `1342-5`). Corrige bug em que o aviário `1342` e outros lotes de dígito único eram omitidos silenciosamente por incompatibilidade de chaves na junção com o arquivo `FiltroMissaoEuropa`.

### Alterado
*   **Filtragem de Cargas de Ração Fora de Ordem:** Generalizada a regra zootécnica de consistência cronológica. Agora, qualquer entrega de fase de ração tardia ocorrendo antes de uma fase inicial no mesmo lote (ex: `3_INICIAL2` ou `5_ABATE` entregues antes de `1_PREINICIAL`) é detectada como sobra do ciclo anterior e descartada pelo ETL (antes a lógica cobria apenas o caso de Abate como a primeira entrega absoluta).

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
