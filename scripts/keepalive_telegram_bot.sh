#!/bin/bash

# Diretorios e caminhos
PROJECT_DIR="/home/bruno/labelreprint"
LOG_FILE="$PROJECT_DIR/logs/telegram_bot.log"
LOG_BAK="$PROJECT_DIR/logs/telegram_bot.log.1"
PID_FILE="$PROJECT_DIR/logs/telegram_bot.pid"
LAST_RUN_FILE="$PROJECT_DIR/logs/.last_housekeeping_day"

# Garante que a pasta de logs existe
mkdir -p "$PROJECT_DIR/logs"

# Housekeeping: Mantem no maximo 1 dia de persistencia para proteger o SD card
HOJE=$(date +%d)

if [ -f "$LAST_RUN_FILE" ]; then
    ULTIMO_DIA=$(cat "$LAST_RUN_FILE")
else
    ULTIMO_DIA=""
fi

if [ "$HOJE" != "$ULTIMO_DIA" ]; then
    # Rotaciona e deleta o backup anterior (mantendo apenas o dia anterior)
    if [ -f "$LOG_BAK" ]; then
        rm -f "$LOG_BAK"
    fi
    if [ -f "$LOG_FILE" ]; then
        mv "$LOG_FILE" "$LOG_BAK"
    fi
    # Cria novo log limpo
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Novo ciclo de log iniciado (housekeeping ativo)." > "$LOG_FILE"
    echo "$HOJE" > "$LAST_RUN_FILE"
else
    # Evita que o log atual cresça indefinidamente limitando o tamanho dele para 2MB
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(wc -c < "$LOG_FILE")
        if [ "$LOG_SIZE" -gt 2097152 ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Log ultrapassou limite de 2MB. Limpando..." > "$LOG_FILE"
        fi
    fi
fi

# Verifica se o bot do Telegram esta ativo
if pgrep -f "run_telegram_bot.py" > /dev/null; then
    # Opcional: registrar liveness a cada execucao do watchdog
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Watchdog: Bot do Telegram esta rodando normalmente." >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Watchdog: Bot do Telegram nao localizado. Inicializando..." >> "$LOG_FILE"
    cd "$PROJECT_DIR"
    

    
    # Executa o bot em background usando o venv redirecionando stdout e stderr para o log
    nohup venv/bin/python3 scripts/run_telegram_bot.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Watchdog: Bot iniciado com PID $(cat $PID_FILE)." >> "$LOG_FILE"
fi
