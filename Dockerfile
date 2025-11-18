# Usar uma imagem oficial do Python como base
FROM python:3.11-slim

# Instalar o cron
RUN apt-get update && apt-get install -y cron

# Definir variáveis de ambiente para o Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Criar um diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo de dependências
COPY requirements.txt /app/

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código do projeto para o diretório de trabalho
COPY . /app/

# Dar permissão de execução para o script
RUN chmod +x /app/scripts/run_processar_pontos.sh

# Adicionar o crontab
COPY scripts/crontab /etc/cron.d/processar-pontos-cron
RUN crontab /etc/cron.d/processar-pontos-cron