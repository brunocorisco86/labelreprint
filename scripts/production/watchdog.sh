#!/bin/bash
# ==============================================================================
# Script Watchdog - Monitoramento do Webserver do Portal de Rótulos (Flask)
# Executado via Cron no Raspberry Pi 3B (Alpine Linux)
# ==============================================================================

# Caminhos absolutos
APP_DIR="/home/bruno/labelreprint"
LOG_FILE="$APP_DIR/logs/watchdog.log"
PORT=5001
URL="http://127.0.0.1:$PORT/"

mkdir -p "$(dirname "$LOG_FILE")"

# Função de log
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Verifica se o webserver está respondendo na porta 5000
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$URL" || echo "000")

if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 302 ]; then
    # Opcional: descomente a linha abaixo para registrar logs de sucesso
    # log_message "OK - Portal Web respondendo na porta $PORT (Status: $HTTP_STATUS)"
    exit 0
else
    log_message "ALERTA - Portal Web inativo ou lento (HTTP Status: $HTTP_STATUS). Iniciando recuperação..."
    
    # 1. Tentativa de reinicialização via OpenRC (se rodar como root)
    if [ "$EUID" -eq 0 ]; then
        log_message "Tentando reiniciar via OpenRC (rc-service)..."
        rc-service labelreprint restart >> "$LOG_FILE" 2>&1
        sleep 5
        
        # Valida novamente
        NEW_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$URL" || echo "000")
        if [ "$NEW_STATUS" -eq 200 ]; then
            log_message "SUCESSO - Serviço reiniciado com sucesso via OpenRC."
            exit 0
        else
            log_message "FALHA - Falha ao reiniciar via OpenRC. Status novo: $NEW_STATUS"
        fi
    fi
    
    # 2. Fallback de reinicialização direta (caso rode como usuário comum ou OpenRC falhar)
    log_message "Buscando processos Python órfãos na porta $PORT para limpar..."
    PID=$(lsof -t -i:$PORT || netstat -lntp 2>/dev/null | grep ":$PORT" | awk '{print $7}' | cut -d/ -f1 || true)
    if [ -n "$PID" ]; then
        log_message "Matando processo antigo PID $PID..."
        kill -9 "$PID" 2>/dev/null || true
        sleep 2
    fi
    
    log_message "Iniciando Flask manualmente em background..."
    cd "$APP_DIR"
    export PYTHONPATH=.
    nohup ./venv/bin/python3 scripts/run_webserver.py >> "$APP_DIR/logs/webserver_stdout.log" 2>> "$APP_DIR/logs/webserver_stderr.log" &
    
    sleep 5
    FINAL_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$URL" || echo "000")
    if [ "$FINAL_STATUS" -eq 200 ]; then
        log_message "SUCESSO - Servidor recuperado e rodando manualmente em background."
    else
        log_message "CRÍTICO - Falha catastrófica ao reiniciar o Portal Web. Status atual: $FINAL_STATUS"
    fi
fi
