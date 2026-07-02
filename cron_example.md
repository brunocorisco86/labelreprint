# ⏰ Configuração do Cron - Ambiente de Produção (Alpine Linux)

Este documento descreve como configurar e agendar os scripts de manutenção automática (`watchdog.sh` e `keepalive.sh`) usando o daemon `cron` no Raspberry Pi 3B rodando Alpine Linux.

---

## 🛠️ Preparação dos Scripts

Antes de agendar as tarefas, certifique-se de que os scripts de produção possuem permissão de execução:

```bash
# Acesse o diretório da aplicação no Raspberry Pi
cd /home/bruno/labelreprint

# Conceda permissão de execução aos scripts de produção
chmod +x scripts/production/*.sh
```

---

## 📅 Agendamento de Tarefas

O Alpine Linux utiliza o `busybox-crond` por padrão. Há dois tipos de monitoramento que configuramos:

1.  **Watchdog (Monitoramento da Aplicação Web)**: Pode rodar sob o usuário comum (`bruno`). Se o webserver cair, ele restabelece o serviço.
2.  **Keepalive (Monitoramento de Rede/Tailscale)**: Deve rodar como `root` porque pode reiniciar serviços do sistema (OpenRC) ou interfaces de rede físicas se necessário.

### 1. Configurando o Keepalive (Requer privilégios Root)

Edite o crontab do usuário **root**:

```bash
sudo crontab -e
```

Adicione a seguinte linha ao final do arquivo para rodar o monitoramento de rede **a cada 5 minutos**:

```cron
*/5 * * * * /bin/bash /home/bruno/labelreprint/scripts/production/keepalive.sh
```

*Salve e feche o editor (no editor padrão `vi`, pressione `ESC`, digite `:wq` e pressione `Enter`).*

### 2. Configurando o Watchdog (Usuário da Aplicação)

Edite o crontab do usuário **bruno**:

```bash
crontab -e
```

Adicione a seguinte linha ao final do arquivo para verificar o status do Portal Web **a cada 2 minutos**:

```cron
*/2 * * * * /bin/bash /home/bruno/labelreprint/scripts/production/watchdog.sh
```

*Salve e feche o editor.*

---

## 📝 Logs de Execução e Diagnóstico

Os scripts gravam logs detalhados de suas ações para facilitar a auditoria. Você pode monitorá-los em tempo real com os seguintes comandos no Raspberry Pi:

*   **Log do Watchdog (Status do Servidor Flask)**:
    ```bash
    tail -f /home/bruno/labelreprint/logs/watchdog.log
    ```
*   **Log do Keepalive (Rede e VPN Tailscale)**:
    ```bash
    tail -f /home/bruno/labelreprint/logs/keepalive.log
    ```
*   **Logs do Servidor Flask (Stdout/Stderr)**:
    ```bash
    tail -f /home/bruno/labelreprint/logs/webserver_stdout.log
    tail -f /home/bruno/labelreprint/logs/webserver_stderr.log
    ```

---

## 🔍 Validando se o Cron está Ativo

No Alpine Linux, confirme se o serviço do Cron está em execução usando o OpenRC:

```bash
# Verifica o status do serviço crond
rc-service crond status

# Se estiver parado, inicie-o
sudo rc-service crond start

# Garanta que ele inicie no boot do sistema
sudo rc-update add crond default
```
