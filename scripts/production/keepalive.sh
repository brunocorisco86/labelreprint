#!/bin/bash
# ==============================================================================
# Script Keepalive - Mantém conexões de rede e Tailscale ativas
# Executado via Cron no Raspberry Pi 3B (Alpine Linux)
# ==============================================================================

APP_DIR="/home/bruno/labelreprint"
LOG_FILE="$APP_DIR/logs/keepalive.log"

mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# 1. Testar conectividade básica com a LAN pingando o Gateway padrão
GATEWAY=$(ip route | grep default | awk '{print $3}' | head -n 1)
if [ -z "$GATEWAY" ]; then
    # Fallback se não detectar dinamicamente
    GATEWAY="192.168.1.1"
fi

if ping -c 3 -W 3 "$GATEWAY" > /dev/null 2>&1; then
    # LAN OK
    LAN_OK=true
else
    LAN_OK=false
    log_message "ALERTA - Gateway LAN ($GATEWAY) inacessível!"
fi

# 2. Testar conectividade de internet básica (DNS Google)
if ping -c 2 -W 3 8.8.8.8 > /dev/null 2>&1; then
    INTERNET_OK=true
else
    INTERNET_OK=false
    log_message "ALERTA - Internet externa inacessível (ping 8.8.8.8 falhou)!"
fi

# 3. Testar o status do Tailscale
if command -v tailscale > /dev/null 2>&1; then
    TS_STATUS=$(tailscale status 2>/dev/null || echo "daemon-down")
    
    if [ "$TS_STATUS" = "daemon-down" ]; then
        log_message "ALERTA - Daemon do Tailscale não está rodando!"
        if [ "$EUID" -eq 0 ]; then
            log_message "Reiniciando serviço Tailscale via OpenRC..."
            rc-service tailscale restart >> "$LOG_FILE" 2>&1
        fi
    elif echo "$TS_STATUS" | grep -q "Logged out"; then
        log_message "ALERTA - Tailscale está desautenticado (Logged out)."
    else
        # Tailscale rodando e autenticado
        TS_OK=true
    fi
else
    log_message "Aviso: Tailscale não está instalado no sistema."
fi

# Ações corretivas de rede se tudo estiver offline
if [ "$LAN_OK" = false ] && [ "$INTERNET_OK" = false ]; then
    log_message "Interface de rede física parece desconectada. Tentando restaurar..."
    if [ "$EUID" -eq 0 ]; then
        # Reinicia a interface de rede padrão (eth0 ou wlan0) no Alpine
        IFACE=$(ip route | grep default | awk '{print $5}' | head -n 1)
        if [ -n "$IFACE" ]; then
            log_message "Reiniciando interface de rede: $IFACE"
            ifdown "$IFACE" && ifup "$IFACE" >> "$LOG_FILE" 2>&1
        else
            log_message "Reiniciando serviço de redes no Alpine Linux..."
            rc-service networking restart >> "$LOG_FILE" 2>&1
        fi
    else
        log_message "Usuário sem privilégios root. Impossível reiniciar interfaces de rede."
    fi
fi
