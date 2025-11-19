# Usar uma imagem oficial do Python como base
FROM python:3.11-slim

# Instalar o cron e outras dependências
RUN apt-get update && apt-get install -y cron

# Criar e ativar o ambiente virtual
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar apenas os arquivos de dependência primeiro para aproveitar o cache do Docker
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copiar o resto do código da aplicação
COPY . /app
WORKDIR /app

# Adicionar o crontab e definir as permissões corretas
COPY scripts/crontab /etc/cron.d/processar-pontos-cron
RUN chmod 0644 /etc/cron.d/processar-pontos-cron