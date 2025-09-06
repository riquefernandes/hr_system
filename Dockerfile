# Usar uma imagem oficial do Python como base
FROM python:3.11-slim

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