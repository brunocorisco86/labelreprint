#!/bin/bash
# ==============================================================================
# Script de Deploy de Dados - Envia base de dados e .env via SCP para o RPi
# Executado LOCALMENTE na máquina do desenvolvedor
# ==============================================================================

set -e

# Configurações de caminhos
DB_PATH="data/processed/entregas_processadas.db"

# 1. Validações Locais de Integridade (Fail-Fast)
echo "======================================================================"
echo "    INICIANDO VALIDAÇÕES PRÉ-DEPLOY LOCAL                         "
echo "======================================================================"

# 1.1. Verificar se as credenciais SMTP no .env local estão preenchidas
if [ -f ".env" ]; then
    echo "Verificando configurações de e-mail (SMTP) no .env local..."
    python3 -c "
from dotenv import dotenv_values
config = dotenv_values('.env')
required = ['SMTP_SERVER', 'SMTP_PORT', 'SMTP_USERNAME', 'SMTP_PASSWORD', 'SMTP_FROM_EMAIL']
missing = [k for k in required if not config.get(k)]
if missing:
    print(f'❌ ERRO: Configurações de SMTP incompletas no seu .env local: {missing}')
    print('O deploy foi abortado para evitar que o envio de e-mails em produção seja desativado.')
    exit(1)
else:
    print('✅ Configurações de e-mail (SMTP) validadas com sucesso.')
" || exit 1
else
    echo "❌ ERRO: Arquivo .env local não encontrado. O deploy foi abortado."
    exit 1
fi

# 1.2. Verificar integridade e tabelas obrigatórias no banco de dados local
if [ -f "$DB_PATH" ]; then
    echo "Verificando tabelas da base de dados SQLite local..."
    python3 -c "
import sqlite3
conn = sqlite3.connect('$DB_PATH')
cursor = conn.cursor()
tables = [r[0] for r in cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
required = ['EntregasRacao', 'Fazendas', 'FiltroLotesAtivos', 'Regioes']
missing = [t for t in required if t not in tables]
if missing:
    print(f'❌ ERRO: Tabelas obrigatórias ausentes na base SQLite local: {missing}')
    print('Por favor, execute o ETL localmente primeiro: venv/bin/python3 src/core/data_manager.py')
    exit(1)
else:
    print('✅ Tabelas da base de dados SQLite validadas com sucesso.')
" || exit 1
else
    echo "❌ ERRO: Base de dados SQLite local não encontrada em $DB_PATH. Execute o ETL antes de fazer o deploy."
    exit 1
fi

# Configurações de SSH
SSH_ALIAS="peixe" # Configurado no ~/.ssh/config do usuário
REMOTE_DIR="/home/bruno/labelreprint"

echo "======================================================================"
echo "    ENVIANDO DADOS LOCAIS PARA O AMBIENTE DE PRODUÇÃO (RPi 3B)       "
echo "======================================================================"
echo "SSH Alias: $SSH_ALIAS"
echo "Diretório Remoto: $REMOTE_DIR"
echo "----------------------------------------------------------------------"

# 2. Verificar conexão SSH
echo "Testando conexão SSH com '$SSH_ALIAS'..."
if ssh -q -o ConnectTimeout=5 "$SSH_ALIAS" exit; then
    echo "Conexão SSH estabelecida com sucesso!"
else
    echo "Erro: Não foi possível conectar a '$SSH_ALIAS'."
    echo "Certifique-se de que o Raspberry Pi está ligado, na mesma rede local ou Tailscale,"
    echo "e que o alias 'peixe' está configurado no seu ~/.ssh/config."
    exit 1
fi

# 3. Criar estrutura de diretórios remotos
echo -e "\nGarantindo que os diretórios existem no Raspberry Pi..."
ssh "$SSH_ALIAS" "mkdir -p $REMOTE_DIR/data/processed $REMOTE_DIR/data/raw $REMOTE_DIR/Export $REMOTE_DIR/logs"

# 4. Enviar o arquivo .env
if [ -f ".env" ]; then
    echo -e "\nEnviando arquivo de configuração (.env)..."
    scp .env "$SSH_ALIAS:$REMOTE_DIR/.env"
    echo ".env copiado com sucesso!"
else
    echo "Aviso: Arquivo .env local não encontrado para envio."
fi

# 5. Enviar a base de dados SQLite processada
if [ -f "$DB_PATH" ]; then
    echo -e "\nEnviando banco de dados SQLite ($DB_PATH)..."
    scp "$DB_PATH" "$SSH_ALIAS:$REMOTE_DIR/data/processed/"
    echo "Banco de dados copiado com sucesso!"
else
    echo "Aviso: Banco de dados local não encontrado em $DB_PATH. Pulando envio do BD."
fi

# 6. Enviar a pasta data/raw/ (opcional)
REPLY="n"
if [ -t 0 ]; then
    read -p "Deseja copiar a pasta de dados brutos (data/raw/) para a produção? (s/N): " -n 1 -r || true
    echo
else
    echo -e "\nAmbiente não-interativo detectado. Pulando cópia de dados brutos."
fi

if [[ $REPLY =~ ^[Ss]$ ]]; then
    if [ -d "data/raw" ] && [ "$(ls -A data/raw)" ]; then
        echo "Copiando dados brutos via SCP..."
        scp -r data/raw/* "$SSH_ALIAS:$REMOTE_DIR/data/raw/"
        echo "Dados brutos copiados com sucesso!"
    else
        echo "Aviso: Pasta data/raw/ vazia ou inexistente no local."
    fi
fi

# 7. Limpar processos órfãos e reiniciar o serviço na produção
echo -e "\nLimpando processos órfãos e reiniciando o serviço na produção..."
ssh "$SSH_ALIAS" "
    if pgrep -f 'python.*run_webserver[.]py' > /dev/null; then
        echo '  -> Encontradas instâncias ativas de run_webserver.py. Finalizando...'
        pkill -9 -f 'python.*run_webserver[.]py' || true
    fi
    echo '  -> Reiniciando o serviço OpenRC...'
    rc-service labelreprint restart || (rc-service labelreprint zap && rc-service labelreprint start)
"

echo "----------------------------------------------------------------------"
echo "Deploy de dados e reinicialização de serviço concluídos com sucesso!"
echo "======================================================================"


