#!/bin/bash
# ==============================================================================
# Script de Comissionamento e Setup - Portal Rótulos C.Vale (Raspberry Pi 3B)
# Sistema Operacional Alvo: Alpine Linux
# ==============================================================================

set -e

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # Sem cor

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}    INICIALIZANDO COMISSIONAMENTO DO AMBIENTE DE PRODUÇÃO (ALPINE)    ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Validação de usuário root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Erro: Este script deve ser executado como root (ou via sudo).${NC}"
  exit 1
fi

# 2. Configuração de Repositórios do Alpine (Community é necessário para pacotes python)
echo -e "\n${YELLOW}[1/6] Configurando repositórios Alpine Linux...${NC}"
ALPINE_VERSION=$(cut -d. -f1,2 /etc/alpine-release)
echo "https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION}/main" > /etc/apk/repositories
echo "https://dl-cdn.alpinelinux.org/alpine/v${ALPINE_VERSION}/community" >> /etc/apk/repositories
apk update

# 3. Instalação de dependências do sistema e pacotes Python pré-compilados
# RPi 3B tem apenas 1GB de RAM. Compilar pandas/numpy via pip causará estouro de memória (OOM).
# Instalamos pacotes nativos pré-compilados do Alpine e usaremos --system-site-packages no virtualenv.
echo -e "\n${YELLOW}[2/6] Instalando dependências e pacotes pré-compilados do Alpine...${NC}"
apk add --no-cache \
    bash \
    git \
    curl \
    openssh \
    tzdata \
    sqlite \
    tailscale \
    python3 \
    py3-pip \
    py3-virtualenv \
    py3-pandas \
    py3-numpy \
    py3-openpyxl \
    py3-pydantic \
    py3-flask

# 4. Configuração de Timezone (Fuso Horário)
echo -e "\n${YELLOW}[3/6] Configurando fuso horário (America/Sao_Paulo)...${NC}"
if [ -f /usr/share/zoneinfo/America/Sao_Paulo ]; then
    cp /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
    echo "America/Sao_Paulo" > /etc/timezone
    echo -e "${GREEN}Fuso horário configurado com sucesso: $(date)${NC}"
else
    echo -e "${RED}Aviso: Arquivo de timezone não encontrado. Mantendo padrão.${NC}"
fi

# 5. Configuração e Habilitação de Serviços Essenciais (OpenRC)
echo -e "\n${YELLOW}[4/6] Configurando inicialização de serviços no OpenRC...${NC}"
# SSH daemon
rc-update add sshd default || true
rc-service sshd start || true

# Cron daemon
rc-update add crond default || true
rc-service crond start || true

# Tailscale daemon
rc-update add tailscale default || true
rc-service tailscale start || true

echo -e "${GREEN}Serviços de sistema configurados e iniciados.${NC}"
echo -e "${YELLOW}Dica: Se o Tailscale for novo, execute 'tailscale up' no terminal para autenticar.${NC}"

# 6. Criação da estrutura de diretórios da aplicação e configuração do Virtualenv
APP_DIR="/home/bruno/labelreprint"
echo -e "\n${YELLOW}[5/6] Preparando diretório da aplicação em ${APP_DIR}...${NC}"

# Cria pasta se não existir
mkdir -p "$APP_DIR"
mkdir -p "$APP_DIR/data/processed"
mkdir -p "$APP_DIR/data/raw"
mkdir -p "$APP_DIR/Export"
mkdir -p "$APP_DIR/logs"

# Garante propriedade do usuário bruno
chown -R bruno:bruno "$APP_DIR" || true

# Criação do Virtualenv isolado herdando pacotes globais do Alpine (importante para pandas/numpy)
echo -e "\n${YELLOW}[6/6] Configurando ambiente Python (Virtualenv herdando pacotes do sistema)...${NC}"
cd "$APP_DIR"
su bruno -c "python3 -m venv --system-site-packages venv"

# Instala as demais dependências que instalam rápido pelo pip
echo -e "${YELLOW}Instalando pacotes pip restantes (reportlab, pypdf, python-dotenv, typer)...${NC}"
su bruno -c "./venv/bin/pip install --upgrade pip" || true
su bruno -c "./venv/bin/pip install python-dotenv reportlab pypdf typer"

# 7. Criação do script de Inicialização OpenRC para o Webserver
echo -e "\n${YELLOW}[BÔNUS] Criando serviço OpenRC para inicialização automática do Portal Web...${NC}"
INIT_SCRIPT="/etc/init.d/labelreprint"
cat << 'EOF' > "$INIT_SCRIPT"
#!/sbin/openrc-run

name="Portal Reimpressao Rotulos C.Vale"
description="Servico Flask do Portal de Reimpressao de Rotulos C.Vale"
command="/home/bruno/labelreprint/venv/bin/python3"
command_args="/home/bruno/labelreprint/scripts/run_webserver.py"
command_background="yes"
directory="/home/bruno/labelreprint"
pidfile="/run/labelreprint.pid"
output_log="/home/bruno/labelreprint/logs/webserver_stdout.log"
error_log="/home/bruno/labelreprint/logs/webserver_stderr.log"

depend() {
    need net
    after sshd tailscale
}

start_pre() {
    # Garante que a pasta de logs existe
    mkdir -p /home/bruno/labelreprint/logs
    chown -R bruno:bruno /home/bruno/labelreprint/logs
}
EOF

chmod +x "$INIT_SCRIPT"
rc-update add labelreprint default || true
echo -e "${GREEN}Serviço 'labelreprint' criado e adicionado à inicialização padrão!${NC}"
echo -e "${YELLOW}Para gerenciar o serviço, use: rc-service labelreprint [start|stop|restart|status]${NC}"

echo -e "\n${GREEN}======================================================================${NC}"
echo -e "${GREEN}      COMISSIONAMENTO CONCLUÍDO COM SUCESSO NO RASPBERRY PI!         ${NC}"
echo -e "${GREEN}======================================================================${NC}"
echo -e "Próximos passos:"
echo -e "1. No seu PC local, execute o script de deploy dos dados: scripts/production/deploy_data.sh"
echo -e "2. No Raspberry Pi, faça login e autentique o Tailscale: sudo tailscale up"
echo -e "3. Inicie o portal web: sudo rc-service labelreprint start"
echo -e "4. Configure o crontab usando as instruções em cron_example.md"
echo -e "======================================================================"
