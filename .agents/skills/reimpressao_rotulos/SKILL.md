---
name: reimpressao_rotulos
description: Orientações de engenharia de software e regras de negócio para manutenção do sistema de Impressão de Rótulos de Ração da C.Vale.
---

# 🛠️ Skill de Impressão de Rótulos de Ração C.Vale

Esta skill fornece diretrizes técnicas e operacionais para manutenção, depuração e expansão do sistema de geração retroativa de rótulos de ração.

## 📐 Arquitetura da Solução

O sistema baseia-se em um pipeline de ETL integrado que extrai transações de entrega, limpa redundâncias operacionais, e realiza a mesclagem física de dados dinâmicos sobre templates PDF originais:

1.  **Camada de Dados**: SQLite (`data/processed/entregas_processadas.db`) e Pandas.
2.  **Camada de PDF**: ReportLab para gerar o canvas overlay de texto e pypdf para mesclar com o PDF original do template.
3.  **Mapeamento**:
    *   [templates.json](file:///home/bruno/Documentos/1_C.VALE/2%20-%20PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/config/templates.json): Coordenadas (X, Y) e alinhamentos de texto para cada arquivo de template físico.
    *   [shelf_life.json](file:///home/bruno/Documentos/1_C.VALE/2%20-%20PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/config/shelf_life.json): Shelf-life padrão por fabricante de ração.
4.  **Regras de ETL e Consistência**:
    *   **Normalização de Lote composto**: `FazendaLote` é normalizado para o formato `{fazenda}-{lote}` sem zeros à esquerda (ex: `1342-5`), garantindo correspondência exata entre planilhas operacionais e de auditoria.
    *   **Filtragem de Inversões de Fase (Sobras)**: Cargas entregues com fase tardia antes de fases mais jovens no mesmo lote (ex: `3_INICIAL2` ou `5_ABATE` antes de `1_PREINICIAL`) são filtradas e descartadas como sobras do lote anterior.

## 📏 Regras de Escrita e Coordenadas

### Sistema de Eixo Y Invertido (Origem no Topo)
*   **Origem (0, 0)**: Canto Superior Esquerdo da página (X=0 na esquerda, Y=0 no topo).
*   **Tradução Interna**: O preenchedor realiza a conversão automática: `y_reportlab = altura_pagina - y_json`.

### Alinhamento e Aspect Ratio
*   **Orientação Nativa**: O preenchedor chama `page.transfer_rotation_to_content()` para reconfigurar páginas com rotação lógica (como `/Rotate 90`), tornando-as fisicamente em paisagem (`842x595`) com `/Rotate 0` no dicionário.

### Lote Impresso
*   **Lógica**: O campo `lote` impresso representa o **lote de fabricação da ração** (data de fabricação formatada como **`DDMMAA`**).
    *   *Exemplo*: Se a ração possui data de fabricação `30/06/2026`, o lote impresso é **`300626`**.

## 🚀 Como Executar e Validar

### 1. Execução do Pipeline de Ponta a Ponta
Para rodar todo o sistema do início ao fim (sincronizar templates, gerar grades, executar ETL/MER e gerar os PDFs consolidados de produção):
```bash
PYTHONPATH=. venv/bin/python3 scripts/run_pipeline_ponta_a_ponta.py
```

### 2. Geração Segmentada (Filtro por Tipo de Ração)
*   **Priorizar GlobalGap (Exclusivos C.Vale):**
    ```bash
    PYTHONPATH=. venv/bin/python3 scripts/run_pipeline_ponta_a_ponta.py --tipo GG
    ```
*   **Apenas Comuns (Terceiros e C.Vale não-GG):**
    ```bash
    PYTHONPATH=. venv/bin/python3 scripts/run_pipeline_ponta_a_ponta.py --tipo CM
    ```

### 3. Geração Física de Amostragem de Teste (20 Lotes)
```bash
rm -rf Export/*/ && PYTHONPATH=. venv/bin/python3 scripts/generate_test_lotes.py
```

### 4. Execução da Suíte de Testes
```bash
venv/bin/pytest tests/test_aviario_lote_generation.py -v -s
```

### 5. Inicialização do Portal Web Local
Para iniciar o servidor Flask em localhost:
```bash
PYTHONPATH=. venv/bin/python3 scripts/run_webserver.py
```

### 6. Teste de Autenticação e Credenciais SMTP
Para testar a conexão SMTP do `.env` e enviar um e-mail de teste no console interativo:
```bash
PYTHONPATH=. venv/bin/python3 scripts/test_smtp.py
```

## 🖥️ Administração do Ambiente de Produção

### 1. Acesso SSH ao Host (Alpine Linux)
*   **Acesso Local (na LAN)**:
    ```bash
    ssh peixe
    ```
*   **Acesso Remoto (via Tailscale)**:
    ```bash
    ssh peixe-remoto
    ```
    *(Nota: A chave pública está salva no host remoto permitindo conexão sem senha para o usuário `root` no IP `100.74.64.89`)*

### 2. Gerenciamento do Serviço do Portal Web (OpenRC)
O portal é gerenciado como um serviço do OpenRC chamado `labelreprint`.
*   **Verificar Status**:
    ```bash
    ssh peixe-remoto "rc-service labelreprint status"
    ```
*   **Reiniciar o Serviço**:
    ```bash
    ssh peixe-remoto "rc-service labelreprint restart"
    ```
*   **Tratamento de Falhas (Processo Órfão / Estado Crashed)**:
    Se o reinício falhar devido a processos Flask que se recusam a encerrar (erro `start-stop-daemon: 1 process refused to stop`), limpe o estado do OpenRC e force a reinicialização:
    ```bash
    ssh peixe-remoto "pkill -9 -f 'run_webserver.py' && rc-service labelreprint zap && rc-service labelreprint start"
    ```

