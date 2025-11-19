#!/bin/sh

# As variáveis de ambiente, o diretório de trabalho e o PATH do python
# já são configurados diretamente no Dockerfile e no docker-compose.
# O script agora apenas executa o comando de gerenciamento.
python3 /app/manage.py processar_pontos