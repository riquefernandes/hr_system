#!/bin/sh

# Adiciona um log para sabermos que o cron está rodando
echo "Cron job 'processar_pontos' executado em: $(date)"

# Executa o comando de gerenciamento do Django
# O diretório de trabalho já é /app, conforme definido no Dockerfile
python manage.py processar_pontos