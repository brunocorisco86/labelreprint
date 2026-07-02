# Portal de Impressão de Rótulos de Ração - C.Vale

> [!NOTE]
> **Status do Projeto: Marco Concluído (100% Funcional - Versão 2.0.0)**  
> As especificações iniciais e as expansões interativas (Abas, E-mails e WhatsApp) foram totalmente concluídas e integradas. A documentação completa de produção e instruções operacionais encontram-se no [README.md](file:///home/bruno/Documentos/1_C.VALE/2 - PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/README.md) e na Skill Customizada em [.agents/skills/reimpressao_rotulos/SKILL.md](file:///home/bruno/Documentos/1_C.VALE/2 - PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/.agents/skills/reimpressao_rotulos/SKILL.md).

Este repositório fornece a solução completa para emissão e impressão de rótulos de rações de forma retroativa e sob demanda.

***
## Campos a serem preenchidos no rótulo
temos que preencher 3 campos no rotulo
- Data de Fabricação
- Lote (Data de Fabricação em formato DDMMAA)
- Data de Vencimento (Data de Fabricação + 60 dias)

Observações:
Colocar a variável de dias de shelf-life da 'Data de Vencimento' como uma variavel de ambiente em .env
Teremos diferentes templates de fábricas da C.Vale e de terceiros, teremos um template_resolver.json para definir qual arquivo selecionaremos para o preenchimento. Deveremos criar um algoritmo para a seleção destes arquivos salvos em /assets/RotulosTemplate

---
## Tarefas
- Pegar os Rótulos salvos em /assets/RotulosTemplate e criar os campos editaveis em cada template
	- Não sei qual ferramenta podemos usar para extrair as informaçoes do arquivo e definir o campo editavel para que possamos automatizar o preenchimento e impressão em arquivo .pdf
- Definir quais são os tipos de ração pelo nome do arquivo no template para que possamos quando for executar o codigo de impressao em pdf possamos usa-lo
	- Ração GlobalGap e Comum (As GlobalGap possuem GG no nome)
	- Diferentes Tipos de Ração
- Tratar os dados salvos em /data/raw
	- Estatistica descritiva e extração de features de cada pasta
	- Criação de um MER com os campos existentes
		- EntregasRacao é a tabela fato, as demais tabela dimensao
	- Criar um join dos dados e salvar as entregas limpas em um dataset em /data/processed
	- Tratar os dados de entregas de ração para encontrar as entregas para cada lote (AviarioLote)
- Gerar os Arquivos Agrupados conforme exemplo:
	Export
	├── Extensionista
	│   ├── GlobalGap
	│   │   └── Granja
	│   │       └── Fazenda-Lote
	│   │           ├── RFPI050626.pdf
	│   │           └── RFI11006.pdf
	│   └── Comum
	│       └── Granja
	│           └── Fazenda-Lote
	│               ├── RFPI050626.pdf
	│               └── RFI11006.pdf

***
## Regras de Tratamento de Dados
- Existem dois tipos de Ração
	- GlobalGap
	- Comum

***
## Glossário
Extensionista: Veterinario ou Técnico que atende a granja. Pode haver campos onde ele pode ser chamado como Extensionista ou Técnico. Se o dado for numeros ele se refere ao BP (Business Partner number do SAP), daí voce desconsidera. Aplique essa lógica quando estiver fazendo a estatistica descritiva.
Aviario: Local onde são criados os animais, nos datasets pode ser chamado de Fazenda também
Lote de Frango: Concatenação do Aviario + Lote (numero ordinal dos lotes criados no aviario), pode ser chamado de Lote Composto ou AviarioLote
GlobalGap: Certificação Global Gap do aviário. Os lotes destes aviários são destinados para clientes distintos, no template de rótulo de ração pode ser encontrado GG 

***
## Roadmap
- [x] Organize a stack / arquitetura da solução
- [x] Defina as skills necessárias para a execução da tarefa
- [x] Crie subagentes para que possamos dividir melhor as tarefas
- [x] Crie o README.md e primeiras documentação
- [x] Definição do MER dos dados
- [x] Merge dos dados do dataset e criação de um dataset robusto salvo em `/data/processed` (SQLite e Pandas)
- [x] Tratamento de redundâncias, duplicidades e inversões zootécnicas no ETL
- [x] Preparar os rótulos (templates) para receber o preenchimento (Coordenadas no Y-invertido)
- [x] Criação de código para criar as exportações em PDF e unificação com compressão PyPDF
- [x] Geração física de produção com unificação em lote e geração de sumário financeiro
- [x] **Portal de Impressão de Rótulos de Ração (Flask Local)**:
	- [x] Aba 1: Emissão Avulsa (Formulário interativo com datas personalizadas).
	- [x] Aba 2: Geração por Núcleo (Processamento em lote via vinculações da planilha).
	- [x] Aba 3: Consulta Lotes e Ficha de Sumário (Visualização retroativa de entregas).
	- [x] Mapeamento dinâmico de validades por fabricante e desduplicação física.
	- [x] Canal de Envio por E-mail (Mime SMTP com Azul Cobalto e Logo C.Vale inline).
	- [x] Canal de Envio para WhatsApp (Markdown vertical otimizado para celulares copiado ao clipboard).
	- [x] Console de Auditoria Web em tempo real (`logs/geracao_manual.log`).
		
***
## Melhorias futuras
- Integração por chamadas de API direta do SAP/Mtech no portal.
- Hospedagem do servidor em VPS on-premises do datacenter da cooperativa.
- Integração com um gateway de mensagens corporativo para envio ativo de notificações.

*** 
## Premissas
- Computação Orientada a Objetos com ferramentas (utils)
- Documentação rica salva em pastas /docs /knowledge /changelog
- Definição do % de completude do Roadmap
- Implementação de testes /tests
- Scripts de comissionamento e testes /scripts
- Tutorial de uso da ferramenta para que for usar no futuro na documentação
- Criação de estatisticas descritivas dos dados de entregas (criado por script acionavel pelo site)
	- Salvo em jupyter notebook ou em markdown
- Os mappings dos campos estarao salvos em /config/templates.json
	
***	
## Identificação dos Rótulos

Cada rótulo gerado deve possuir um identificador único (id_rotulo) com a seguinte estrutura:

{Sequencial_XX}_{TipoRacao}_AV{Fazenda}_{Lote}_{DataFabricacao}

Exemplo:
01_GG_AV123_05_050626

Regras:
- Deve ser determinístico (mesmo input → mesmo id)
- O prefixo sequencial de dois dígitos (ex: 01, 02) é gerado com base na ordem cronológica de entrega das cargas de cada lote, garantindo a ordenação cronológica natural dos arquivos PDFs na pasta
- Será utilizado como nome do arquivo PDF
- Pode ser utilizado para busca no backend

***
## Stack Sugerida

***

# 🧰 ✅ Stack sugerida (modo produção rápida + robusta)

## 🐍 Core

* **Python 3.11+**
* **pandas** → tratamento de dados
* **python-dotenv** → `.env` (shelf-life etc.)

***

## 📄 Manipulação de PDF (ESSENCIAL)

👉 aqui está a decisão mais importante

### ✅ Melhor escolha pra teu caso:

* **reportlab** → escrever texto no PDF (overlay)
* **pypdf** → ler/template base e mesclar

💡 Estratégia:

* Template = PDF fixo
* Você só “escreve por cima” nas coordenadas

***

## 🧠 Dados / estrutura

* **sqlite3 (builtin)** → leve, sem dependência externa
* **pydantic** → validação de dados (evita erro na geração)

***

## ⚙️ CLI (muito importante pra você)

* **typer** → CLI moderna, rápida de implementar

Exemplo futuro:

```
python main.py generate --aviario AV123 --lote 05
```

***

## 🌐 Backend (opcional agora, já preparado)

* **flask** ou **fastapi**

👉 Minha recomendação:

* Começa com **Flask (mais simples pra entregar rápido)**

***

## 🚀 Performance (se precisar escalar rápido)

* **concurrent.futures** (builtin) → paralelismo simples

***

## 🧪 Qualidade

* **pytest** → testes básicos (principalmente id\_rotulo)

***

# 🏗️ Stack final (resumida)

| Camada    | Ferramenta        |
| --------- | ----------------- |
| Dados     | pandas + sqlite   |
| PDF       | reportlab + pypdf |
| Config    | python-dotenv     |
| CLI       | typer             |
| Backend   | flask             |
| Validação | pydantic          |
| Testes    | pytest            |

***

# 📦 ✅ requirements.txt sugerido

Aqui vai já pronto pra copiar:

```txt
pandas==2.2.2
python-dotenv==1.0.1

reportlab==4.2.0
pypdf==4.2.0

typer==0.12.3

flask==3.0.3

pydantic==2.7.1

pytest==8.2.2
```

***

# ⚡ Versão MINIMALISTA (se quiser ir no modo turbo)

Se quiser cortar tudo não essencial pra entregar MUITO rápido:

```txt
pandas
python-dotenv
reportlab
pypdf
typer
```

***

# 🧠 Dicas práticas (baseado no teu cenário real)

## 🔥 1. PDF é o risco maior

Faz um POC antes de tudo:

* abrir template
* escrever “DataFab”
* salvar PDF

👉 Se isso funcionar → projeto inteiro funciona

***

## 🔥 2. Coordenadas dos campos

Você vai precisar mapear:
```python
FIELDS = {
    "data_fabricacao": (x, y),
    "lote": (x, y),
    "data_validade": (x, y),
}
```
 - Já foi salvo um modelo de mapping desses fields em /config/templates

👉 isso é a “chave” do sistema

***

## 🔥 3. Organização de código (já alinhada contigo)

```
/src
  /core
    generator.py
    id_builder.py
  /pdf
    template_loader.py
    writer.py
  /data
    loader.py
    processor.py
  /cli
    main.py
```

***

## 🔥 4. Naming padrão (já com teu ID)

Arquivo final:

```
GG_AV123_05_050626.pdf
```

***

# 🚨 Minha recomendação direta (pra vc entregar rápido)

👉 Ordem de ataque:

1. ✅ Testar geração de PDF com reportlab
2. ✅ Definir coordenadas no template
3. ✅ Criar função `id_rotulo`
4. ✅ Processar dados com pandas
5. ✅ Gerar 1 lote de teste
6. ✅ Rodar em escala

***

# 💡 Insight extra (nível Bruno BI + engenharia)

Se quiser dar um salto sem esforço:

* Salva um `index.csv` com:

```
id_rotulo | caminho_arquivo
```

👉 isso vira backend gratuito pra busca depois

***
