# Regras de Negócio de Remessa e Retorno de Ração

Este documento centraliza as regras de negócio e validações aplicadas aos dados de entregas e recolhas de ração na C.Vale. Essas diretrizes servem de contexto para o desenvolvimento do ETL, interfaces e futuras validações sistêmicas, alinhadas aos pilares do projeto.

---

## 📌 Regra de Identificação de Recolhas e Sobras de Ração

Durante a análise e processamento dos dados de entregas/remessas, regras específicas devem ser aplicadas para identificar devoluções, sobras e possíveis anomalias no processo de entrega física:

### Condições de Filtro
Quando os seguintes campos apresentarem o padrão abaixo:
- **`NumRefRetorno`**: Não nulo (`NOT NULL`)
- **`CodigoTransacao`**: `'Crédito'`
- **`ValorRemessa`**: Menor que zero (`< 0`)
- **`NomeVeiculo`**: `'X'` (ou outro identificador de veículo específico de recolha)

### Interpretação dos Cenários (Fluxo de Decisão)

1. **Recolha por Caminhão Específico**:
   - A combinação acima indica um evento de recolha física de ração no aviário, realizada por um caminhão dedicado a essa atividade (por exemplo, veículo `'X'`).

2. **Sobra de Ração (Final de Lote)**:
   - Se a ração recolhida for classificada como **Ração Abate** (utilizada no final do lote do loteamento do aviário), o evento deve ser interpretado como **recolha de sobra de ração**. Isso ocorre frequentemente após a saída dos animais para o abate.

3. **Possível Anomalia / Problema de Processo**:
   - Se o tipo de ração recolhida for **diferente** de Ração Abate (ex: ração pré-inicial, inicial ou crescimento no final do lote, ou qualquer ração incompatível com o estágio atual do aviário), isso deve ser alertado como um **problema no processo** (desvio de fluxo, erro de programação de carga ou aplicação incorreta).

---

## 🔄 Detecção e Filtragem de Cargas de Ração Fora de Ordem / Sobras do Lote Anterior (ETL)

Nos dados históricos, observa-se que em alguns aviários-lotes (`FazendaLote`), as primeiras entregas registradas cronologicamente podem conter **fases tardias** de ração (como `3_INICIAL2` ou `5_ABATE`), o que contradiz o fluxo natural de nutrição (que deveria iniciar com a `1_PREINICIAL` e progredir em ordem crescente). 

Essas ocorrências representam as **sobras de ração do lote anterior** que foram creditadas ou lançadas de forma tardia/retroativa sob o lote atual por motivos operacionais e logísticos.

### Regra de Tratamento (Algoritmo de Filtragem Generalizado):
Para identificar e filtrar essas cargas fora de ordem no pipeline de ETL, a seguinte lógica de consistência é aplicada:
1. **Mapeamento de Ordem das Fases**: As fases de ração legítimas são mapeadas em ordinais crescentes de `1_PREINICIAL` (1) a `5_ABATE` (5).
2. **Identificação de Menor Fase Subsequente**: Para cada entrega do lote, identifica-se qual a menor fase legítima entregue cronologicamente em qualquer momento posterior no mesmo lote.
3. **Filtro de Inversão**: Se a menor fase subsequente for estritamente menor do que a fase da entrega atual (e maior que 0, para ignorar fases não catalogadas), a entrega atual é marcada como fora de ordem (sobra) e descartada do pipeline.
   * *Exemplo*: Se um lote inicia com cargas de `3_INICIAL2` ou `5_ABATE` e, em seguida, recebe cargas de `1_PREINICIAL`, as cargas iniciais de fases tardias são filtradas e removidas.
4. **Reordenação**: O sequencial de entregas restantes do lote é reordenado para que o primeiro registro legítimo inicie a partir do sequencial `01`.

*Nota: Se o lote contiver apenas entregas de ração tardias (como apenas cargas de abate na janela histórica), elas são mantidas como legítimas de final de ciclo e **não** são descartadas.*

---

## 📋 Desduplicação e Omissão de Emissão de Rótulos (ETL)

Para evitar a poluição de múltiplos PDFs idênticos nos diretórios de exportação e garantir a acurácia dos dados de consumo físico por lote, duas diretrizes adicionais são aplicadas no pipeline:

1. **Desduplicação de Cargas Repetidas**: 
   - No início do processamento de ETL, registros 100% idênticos operacionalmente no banco de dados (mesmo lote, data, hora, número de carga, volume, transação e fórmula) são filtrados e mantidos em registro único.
2. **Omissão por Duplicidade Diária**: 
   - Se ocorrer mais de uma entrega da mesma ração para o mesmo lote no mesmo dia, apenas a primeira entrega cronológica gera um rótulo físico (PDF), evitando duplicidades no diretório.
3. **Omissão por Retorno Integral**: 
   - Se a soma líquida de volume de uma carga (`NumCarga`) for menor ou igual a zero (por ter retornado integralmente à fábrica devido a devoluções/cancelamentos), a emissão do rótulo PDF é suprimida.
   - *Nota: Essas transações continuam disponíveis no banco SQLite e são processadas integralmente nos relatórios de sumário de entregas (`sumario_entregas.txt`) para refletir o histórico financeiro completo.*

---

## 📋 Definição de Lote de Ração Impresso

- **Finalidade**: O campo `lote` impresso fisicamente no rótulo PDF representa o **lote de fabricação da ração**, e não o lote de criação zootécnica de aves do aviário.
- **Formatação**: O lote de ração é gerado a partir da data de fabricação no padrão **`DDMMAA`**.
  - *Exemplo*: Se a ração possui data de fabricação `2026-06-30` (30/06/2026), o lote impresso correspondente é **`300626`**.

---

## 🔗 Relação com os Pilares do Projeto

Essas regras e validações se conectam diretamente com a estratégia global do projeto:

- **Processos Otimizados (Confirmação de Pedidos e Fluxos)**: A identificação automática de sobras e anomalias de recolha previne erros de faturamento, evita retrabalho operacional e melhora a acurácia dos inventários físicos.
- **Tecnologia Habilitadora (TMS e Sensores)**: O cruzamento dos dados de pesagem e veículo (TMS) com o nível dos silos (sensores) valida se a quantidade recolhida condiz com a sobra real estimada no aviário.
- **Comunicação Eficiente**: A interface centralizada deve alertar a equipe operacional de logística ou os extensionistas quando uma recolha com padrão suspeito (ração diferente de abate) for detectada.
