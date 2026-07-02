# 🔄 Diretrizes de CI/CD e Ambientes - Portal de Rótulos C.Vale

Este guia estabelece os pilares, fluxos e regras que os agentes de IA (como Antigravity) e desenvolvedores humanos devem seguir para manter a integridade operacional da aplicação entre o ambiente local (desenvolvimento) e o Raspberry Pi 3B (produção).

---

## 💻 1. Ambiente de Desenvolvimento (Local)
O desenvolvimento, correções e testes ocorrem exclusivamente no ambiente local antes do deploy.

*   **Validação Antes do Commit**: Antes de commitar qualquer mudança estrutural, é mandatório rodar a suíte de testes do projeto:
    ```bash
    venv/bin/pytest tests/test_aviario_lote_generation.py -v -s
    ```
*   **Tratamento de Dados Proprietários**: Os dados de produção (SQLite e planilhas em `data/`) são confidenciais e estão declarados no `.gitignore`. Nunca altere o `.gitignore` para versionar esses arquivos.
*   **Versionamento de Configurações**: Variáveis de ambiente como credenciais de SMTP ou endereços IPs físicos (`LAN_IP`, `TAILSCALE_IP`) devem permanecer exclusivamente no arquivo `.env` local e não rastreado. Atualize sempre o `.env.example` com placeholders caso novas variáveis sejam introduzidas.

---

## 🚀 2. Processo de Deploy e Atualização

### A. Fluxo de Código (Atualizações da Aplicação)
Toda a lógica e templates visuais atualizados no repositório remoto Git devem ser puxados na produção via pull:
1.  Desenvolva, valide os testes e envie para o Git localmente:
    ```bash
    git add <arquivos>
    git commit -m "feat/fix: descrição da alteração"
    git push origin master
    ```
2.  No Raspberry Pi de produção (acessado via `ssh peixe`), realize o pull:
    ```bash
    cd /home/bruno/labelreprint
    git pull
    ```
3.  Reinicie o serviço web no Raspberry Pi para carregar as alterações de código:
    ```bash
    sudo rc-service labelreprint restart
    ```

### B. Fluxo de Dados (Bancos de Dados e Variáveis)
Os dados persistidos no banco de dados SQLite local devem ser sincronizados via cópia física direta, já que são ignorados pelo Git:
*   Execute o script local de sincronização:
    ```bash
    bash scripts/production/deploy_data.sh
    ```
    *Este script usa SCP sob o alias `peixe` para atualizar a base `data/processed/entregas_processadas.db` e o arquivo `.env` remoto.*

---

## 🛠️ 3. Comissionamento (Novo Ambiente de Produção)
Para configurar um novo Raspberry Pi ou reconfigurar o atual rodando Alpine Linux:
1.  Clone o repositório remotamente no Pi.
2.  Execute o script de comissionamento de sistema como `root`:
    ```bash
    sudo bash scripts/production/setup_alpine.sh
    ```
    *O setup configura as dependências pré-compiladas via apk (economizando RAM), fuso horário brasileiro, inicializa os serviços de rede/Tailscale/cron e configura o arquivo de serviço OpenRC `/etc/init.d/labelreprint`.*

---

## ⏰ 4. Manutenção e Monitoramento (Cron)
As manutenções na produção rodam automaticamente via cron. As regras estão descritas em [cron_example.md](file:///home/bruno/Documentos/1_C.VALE/2%20-%20PROJETOS/10_ROTULOS_REIMPRESSAO/labelreprint/cron_example.md):
*   **Watchdog (`watchdog.sh`)**: Executa a cada 2 minutos sob o usuário local para garantir que o Flask responda na porta 5000.
*   **Keepalive (`keepalive.sh`)**: Executa a cada 5 minutos sob root para restaurar VPN e interfaces de rede.

Se você precisar depurar problemas na produção, confira os logs gerados em `/home/bruno/labelreprint/logs/`.
