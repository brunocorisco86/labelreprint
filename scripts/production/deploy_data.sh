#!/bin/bash
# ==============================================================================
# Script de Deploy de Dados - Envia base de dados e .env via SCP para o RPi
# Executado LOCALMENTE na máquina do desenvolvedor
# ==============================================================================

set -e

# Configurações de SSH
SSH_ALIAS="peixe" # Configurado no ~/.ssh/config do usuário
REMOTE_DIR="/home/bruno/labelreprint"

echo "======================================================================"
echo "    ENVIANDO DADOS LOCAIS PARA O AMBIENTE DE PRODUÇÃO (RPi 3B)       "
echo "======================================================================"
echo "SSH Alias: $SSH_ALIAS"
echo "Diretório Remoto: $REMOTE_DIR"
echo "----------------------------------------------------------------------"

# 1. Verificar conexão SSH
echo "Testando conexão SSH com '$SSH_ALIAS'..."
if ssh -q -o ConnectTimeout=5 "$SSH_ALIAS" exit; then
    echo "Conexão SSH estabelecida com sucesso!"
else
    echo "Erro: Não foi possível conectar a '$SSH_ALIAS'."
    echo "Certifique-se de que o Raspberry Pi está ligado, na mesma rede local ou Tailscale,"
    echo "e que o alias 'peixe' está configurado no seu ~/.ssh/config."
    exit 1
fi

# 2. Criar estrutura de diretórios remotos
echo -e "\nGarantindo que os diretórios existem no Raspberry Pi..."
ssh "$SSH_ALIAS" "mkdir -p $REMOTE_DIR/data/processed $REMOTE_DIR/data/raw $REMOTE_DIR/Export $REMOTE_DIR/logs"

# 3. Enviar o arquivo .env
if [ -f ".env" ]; then
    echo -e "\nEnviando arquivo de configuração (.env)..."
    scp .env "$SSH_ALIAS:$REMOTE_DIR/.env"
    echo ".env copiado com sucesso!"
else
    echo "Aviso: Arquivo .env local não encontrado para envio."
fi

# 4. Enviar a base de dados SQLite processada
DB_PATH="data/processed/entregas_processadas.db"
if [ -f "$DB_PATH" ]; then
    echo -e "\nEnviando banco de dados SQLite ($DB_PATH)..."
    scp "$DB_PATH" "$SSH_ALIAS:$REMOTE_DIR/data/processed/"
    echo "Banco de dados copiado com sucesso!"
else
    echo "Aviso: Banco de dados local não encontrado em $DB_PATH. Pulando envio do BD."
fi

# 5. Enviar a pasta data/raw/ (opcional - pergunta ao usuário)
read -p "Deseja copiar a pasta de dados brutos (data/raw/) para a produção? (s/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Ss]$ ]]; then
    if [ -d "data/raw" ] && [ "$(ls -A data/raw)" ]; then
        echo "Copiando dados brutos via SCP..."
        scp -r data/raw/* "$SSH_ALIAS:$REMOTE_DIR/data/raw/"
        echo "Dados brutos copiados com sucesso!"
    else
        echo "Aviso: Pasta data/raw/ vazia ou inexistente no local."
    fi
fi

echo "----------------------------------------------------------------------"
echo "Deploy de dados concluído!"
echo "Para atualizar o código do Portal na produção, acesse via SSH:"
echo "  ssh peixe"
echo "E dentro do diretório, rode: git pull"
echo "======================================================================"
