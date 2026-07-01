# Relatório de Estatísticas Descritivas: Filtro de Lotes Gerais (Ativos, Fechados e Abatidos)

Este documento apresenta a análise descritiva dos dados contidos no arquivo [FiltroLotesAtivos.xlsx](file:////home/brunoconter/Documentos/1_C.VALE/2 - PROJETOS/10_REIMPRESSAO_ROTULOS/data/raw/FiltroLotesAtivos/FiltroLotesAtivos.xlsx) e a composição da base de dados de entregas de ração processadas no SQLite.

---

## 📊 1. Resumo Geral do Arquivo de Filtro

O arquivo lista os lotes de criação de aves com sua situação no sistema operacional da C.Vale.

| Métrica | Valor | Descrição |
| :--- | :---: | :--- |
| **Total de Registros** | 911 | Cada linha representa um lote único de uma fazenda |
| **Fazendas Distintas** | 911 | Quantidade de propriedades/aviários únicos listados |
| **Números de Lote Distintos** | 163 | Quantidade de identificadores de lote únicos (ex: ciclo de lote) |

---

## 🔄 2. Distribuição de Situação dos Lotes

### Status do Lote no Mtech (`StatusLoteMtech`)
Identifica se o lote está atualmente ativo (alojado/em andamento) ou fechado.

| Status | Quantidade | Percentual |
| :--- | :---: | :---: |
| **Ativo** | 836 | 91.77% |
| **Fechado** | 75 | 8.23% |

### Indicador de Lote Abatido (`LoteAbatido`)
Sinaliza se o lote já passou pelo abate.

| Lote Abatido | Quantidade | Percentual |
| :--- | :---: | :---: |
| **Falso (Não Abatido)** | 832 | 91.33% |
| **Verdadeiro (Abatido)** | 79 | 8.67% |

### Tabela Cruzada: Status Mtech vs Lote Abatido
Frequência absoluta cruzada dos dois status no Excel:

| Status Mtech \ Lote Abatido | Falso (Não Abatido) | Verdadeiro (Abatido) |
| :--- | :---: | :---: |
| **Ativo** | 832 | 4 |
| **Fechado** | 0 | 75 |

*Nota:* Há 4 lotes marcados como "Ativo" no Mtech que já possuem registro de Lote Abatido como Verdadeiro, o que pode representar um breve período de transição/atualização no sistema Mtech.

---

## 📅 3. Análise Temporal (Alojamento e Abate)

### Data de Alojamento (`DataAlojamento`)
- **Primeiro Alojamento (Min):** `2026-05-11`
- **Mediana dos Alojamentos:** `2026-06-05`
- **Último Alojamento (Max):** `2026-07-01`

### Data de Abate (`DataAbate`)
- **Total de registros preenchidos:** `78` (8.56% dos lotes)
- **Total de registros nulos (sem abate):** `833` (91.44% dos lotes)
- **Primeiro Abate (Min):** `2026-06-23`
- **Último Abate (Max):** `2026-06-30`

---

## 🔌 4. Composição da Base de Dados Filtrada (`EntregasRacao`)

O pipeline de ETL foi configurado para **manter todas as entregas cujos lotes estejam presentes no arquivo** `FiltroLotesAtivos.xlsx`, independentemente do status operacional do lote (sejam ativos, fechados ou abatidos). As entregas pertencentes a lotes fora desta listagem foram descartadas.

A base de entregas de ração no SQLite (`data/processed/entregas_processadas.db`) está atualmente composta por:

| Categoria do Lote | Lotes no DB | Entregas no DB | % das Entregas no DB | Descrição |
| :--- | :---: | :---: | :---: | :--- |
| **Lotes Ativos** | 815 | 4,872 | 83.11% | Lotes operacionais atualmente em andamento |
| **Lotes Fechados** | 75 | 990 | 16.89% | Lotes concluídos e abatidos incluídos na base |
| **Total da Base Processada** | **890** | **5,862** | **100.00%** | **Entregas salvas no SQLite** |

### Conclusão da Análise
Com a remoção da restrição de status no ETL, o banco de dados preserva o histórico de todos os lotes listados na planilha de filtros. Isso nos fornece um escopo de **5,862 entregas** no total distribuidas em **890 lotes** (ativos e fechados), garantindo a cobertura para relatórios retroativos e auditorias de consumo de ração tanto de lotes ativos quanto de lotes recentemente concluídos.
