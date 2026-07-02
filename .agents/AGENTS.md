# Diretrizes Operacionais e Regras de Negócio - Rótulos de Ração C.Vale

Este arquivo contém as diretrizes do comitê do projeto e regras específicas para os agentes de IA operando nesta base de código.

## 📋 Regras de Negócio de Dados

### Validação de Recolhas e Sobras de Ração
Ao analisar, enriquecer ou gerar relatórios a partir de dados de transações de remessa de ração (`EntregasRacao`), considere a seguinte lógica de classificação de recolhas e devoluções:

- **Critérios de Filtro**:
  - `NumRefRetorno` **não é nulo** (`NOT NULL`)
  - `CodigoTransacao` é igual a `'Crédito'`
  - `ValorRemessa` é **menor que zero** (`< 0`)
  - `NomeVeiculo` é igual a `'X'` (ou outro veículo dedicado a recolhas)
- **Cenários**:
  1. **Recolha de Sobra de Ração**: Se a ração em questão for uma ração do tipo **Abate** (usada no final do lote do aviário), classifique/interprete o registro como recolha padrão de sobra de ração pós-abate.
  2. **Possível Anomalia / Problema de Processo**: Se a ração em questão for de **outro tipo (diferente de Abate)**, trate-a como uma anomalia (possível erro operacional ou de carregamento) e gere um alerta apropriado na lógica de negócios ou nos logs de processamento.

### Desduplicação, Normalização e Omissão de Emissão de Rótulos no ETL
Para evitar a poluição de múltiplos PDFs idênticos nos diretórios de exportação e distorções no consumo de rações do lote:
1. **Normalização de FazendaLote**: Códigos compostos de lote são normalizados para remover zeros à esquerda do número do lote (ex: `1342-05` é normalizado para `1342-5`) em todas as tabelas e planilhas, garantindo a consistência das chaves de junção.
2. **Desduplicação de Registros 100% Repetidos**: No início do ETL, são removidas linhas idênticas duplicadas operacionalmente no banco (mesmo `FazendaLote`, `Data`, `HoraTransacao`, `NumCarga`, `QuantidadeEntregue`, `CodigoTransacao`, `NomeFormula`).
3. **Filtro de Cargas Fora de Ordem (Sobras do Lote Anterior)**: Qualquer entrega de ração cuja fase seja cronologicamente posterior a uma fase entregue em data subsequente no mesmo lote (ex: `5_ABATE` ou `3_INICIAL2` antes de `1_PREINICIAL`) é classificada como fora de ordem (sobra de lote anterior) e descartada no ETL.
4. **Omissão por Duplicidade Diária**: Se houver mais de uma entrega da mesma ração no mesmo dia para o mesmo lote, apenas a primeira entrega cronológica gera rótulo (as demais são omitidas).
5. **Omissão por Retorno/Devolução Integral**: Se uma carga (`NumCarga`) foi totalmente devolvida para a fábrica (quantidade líquida total da carga menor ou igual a zero), a emissão do rótulo para ela é totalmente omitida.
Essas cargas inativas recebem `id_rotulo = NULL` no SQLite, mas são preservadas para os balanços dos sumários financeiros (`sumario_entregas.txt`).

### Lote de Ração Impresso
- **Lógica**: O campo `lote` impresso fisicamente no rótulo PDF representa o **lote de fabricação da ração**, e não o lote de criação das aves do aviário. 
- **Valor**: Deve ser preenchido com a data de fabricação da ração formatada no padrão **`DDMMAA`** (ex: se fabricado em `30/06/2026`, o lote impresso será `300626`).

### Sinonímia de Certificações (Global Gap / Global SLP)
- **Lógica**: As siglas **Global Gap** e **Global SLP** (ou simplesmente SLP/GG) referem-se à mesma especificação regulatória e representam **sinônimos** exatos no contexto do projeto.
- **Tratamento**: Quaisquer regras ou filtros zootécnicos voltados a "Global Gap" devem abranger "Global SLP" de forma idêntica (layouts especiais de templates que possuem identificador `GG` ou `SLP`).

## 📐 Alinhamento Técnico e Pilares

1. **Comunicação Eficiente**: Desenvolver e manter uma plataforma centralizada para disponibilizar dados e rótulos de forma clara e ágil.
2. **Processos Otimizados**: Redesenhar fluxos operacionais de confirmação e rastreabilidade de pedidos para minimizar desvios e sobras.
3. **Tecnologia Habilitadora**: Apoiar-se na integração com sistemas legados, TMS (rastreamento de frotas e pesagem) e IoT (sensores de nível nos silos) para validar as operações físicas.

## ✉️ Diretrizes de Comunicação e Compartilhamento

### Configuração e Validação de Canais
- **SMTP**: Todas as credenciais SMTP devem ser mantidas no arquivo `.env`. Para validação segura das credenciais de e-mail, utilize o script interativo `scripts/test_smtp.py`.
- **E-mails Corporativos Padrão**: As comunicações oficiais de testes e emissão manual contam com os destinatários salvos em `config/destinatarios_salvos.json` pre-seeded com:
  - `bruno.conter@cvale.com.br`
  - `vinicius.duarte@cvale.com.br`
  Novos destinatários digitados são validados sintaticamente e salvos de forma incremental no JSON para uso posterior.

### Envio de Sumários por E-mail
- **Identidade Visual**: Os e-mails de sumário seguem a diagramação Azul Cobalto (`#1e3a8a`) e Branco com o logotipo C.Vale inline (`cid:logo_cvale`).
- **Visual de Console**: O texto do sumário de entregas é renderizado em fonte monoespaçada dentro de um container com fundo preto e cor azul claro neon (`#38bdf8`) para mimetizar fielmente a interface do console do Portal Web.

### Compartilhamento para WhatsApp
- **Limitação Mobile**: Telas de smartphones sofrem com quebras de linha automáticas ao receber textos em tabela monoespaçada. Por conta disso, mensagens para WhatsApp devem ser diagramadas estritamente de forma **vertical**.
- **Parser de WhatsApp**: Utilize a rotina de parsing (`parseSumarioToWhatsApp` no frontend) para extrair as entregas de cargas e convertê-las em bullet points (`• DD/MM: Fase - Volume kg (Carga X)`), utilizando emojis e negritos markdown do WhatsApp. O resultado deve ser copiado diretamente para a área de transferência do usuário (Clipboard), evitando redirecionamentos ou abertura de novas abas.
