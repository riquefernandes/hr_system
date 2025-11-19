#!/bin/sh

# Adiciona um log para sabermos que o cron está rodando
echo "Cron job 'processar_pontos' executado em: $(date)"

# Ativa o ambiente virtual
. venv/bin/activate

# Exporta as variáveis de ambiente do banco de dados
export DB_NAME=sistema_rh_db
export DB_USER=admin
export DB_PASS=admin123
export DB_HOST=localhost
export DB_PORT=5432

# Executa o comando de gerenciamento do Django
# O diretório de trabalho já é /app, conforme definido no Dockerfile
python3 manage.py processar_pontos