# Sistema de Gestão de RH (hr_system)

## Descrição

**hr_system** é uma aplicação web desenvolvida em Django para a administração de funcionários de um contact center. O sistema evoluiu para incluir um robusto controle de jornada de trabalho, com registro de ponto, gerenciamento de escalas, banco de horas, relatórios e dashboards para supervisores.

A aplicação é totalmente containerizada com Docker, garantindo um ambiente de desenvolvimento e produção consistente e isolado.

## Funcionalidades Implementadas

### Visão do Administrador (Painel `/admin`)
- **CRUD Completo:** Administradores podem Criar, Ler, Atualizar e Deletar registros para: Funcionários, Cargos, Centros de Custo, Bancos e **Escalas de Trabalho**.
- **Criação Automatizada de Usuários:** Ao criar um novo `Funcionário`, um `User` (login) é criado automaticamente com matrícula e senha provisória.
- **Gestão de Escalas:**
    - Criação de modelos de escalas (dias da semana, horários de entrada/saída, duração de almoço).
    - Associação de uma **escala padrão** a cada cargo.
    - Atribuição de escalas individuais para funcionários, com data de início e fim, diretamente na página do funcionário.
- **Gestão de Pausas:** Definição de regras de pausas (quantidade e duração) por cargo.
- **Fluxo de Aprovação:** Ações customizadas para aprovar em lote solicitações de alteração de endereço e dados bancários feitas pelos funcionários.

### Visão do Funcionário Comum (Frontend)
- **Autenticação Segura:** Tela de login (`/login`) e logout, com **troca de senha obrigatória no primeiro acesso**.
- **Dashboard Pessoal (`/home`):**
    - Visualização completa de dados cadastrais.
    - **Registro de Ponto Virtual:** Funcionalidade para registrar Entrada, Saída e Pausas (café e almoço).
    - **Restrição de Ponto:** O funcionário só pode registrar a entrada dentro de uma janela de tempo permitida em relação à sua escala (ex: 30 min antes e 60 min depois).
    - **Consulta de Escala:** Visualização da escala de trabalho atual.
    - **Horário de Entrada:** Exibe o horário de entrada definido na escala.
    - **Horário de Saída:** Exibe o horário de saída definido na escala.
    - **Dias de Trabalho:** Exibe os dias da semana em que o funcionário deve trabalhar.
    - **Consulta de Banco de Horas:** Visualização do saldo total de horas (positivo ou negativo).
    - **Cronômetro de Tempo Logado:** Exibe o tempo que o funcionário está logado desde a última entrada.
- **Solicitação de Alteração:** Formulários para solicitar alterações de endereço e dados bancários, com histórico e status.

### Visão do Supervisor
- **Dashboard de Equipe (`/supervisor/dashboard`):**
    - Visualização em tempo real do status operacional de todos os funcionários da sua equipe (Disponível, Em Pausa, Offline).
    - A tabela da equipe é atualizada automaticamente a cada 15 segundos (via HTMX).
    - **Cronômetro de Pausa:** Exibe há quanto tempo um funcionário está em pausa.
    - **Alerta de Limite de Pausa:** O cronômetro fica vermelho e em negrito se o funcionário exceder o tempo limite para aquela pausa específica.
- **Relatório de Equipe (`/relatorio/equipe`):**
    - Permite que o supervisor gere um relatório consolidado para sua equipe dentro de um período de datas.
    - O relatório exibe o total de horas extras, horas devidas e faltas injustificadas para cada membro da equipe e também os totais gerais.

### Motor de Processamento (Backend)
- **Cálculo de Banco de Horas Automatizado:** Um comando de gerenciamento (`processar_pontos`) é executado diariamente por um **job agendado (cron)** dentro de um container Docker dedicado. Ele analisa os registros de ponto do dia anterior, compara com a escala do funcionário e calcula o saldo de horas (atrasos, saídas antecipadas, horas extras), registrando tudo na tabela de `BancoDeHoras`.

## Tecnologias Utilizadas

- **Backend:** Python 3.11, Django 5.2
- **Banco de Dados:** PostgreSQL
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla), HTMX
- **Framework CSS:** Bootstrap 5
- **Ambiente:** Docker, Docker Compose
- **Bibliotecas Python Notáveis:**
    - `psycopg2-binary`: Adaptador para PostgreSQL.
    - `django-localflavor`: Para validação de campos brasileiros como o CPF.

## Como Rodar o Projeto Localmente

### Pré-requisitos
- Git
- Docker
- Docker Compose

### Passos para Instalação
1. Clone o repositório:
   ```bash
   git clone https://github.com/riquefernandes/hr_system.git
   cd hr_system
   ```
2. Construa e suba os containers Docker em modo "detached" (background). O compose agora inclui o serviço da aplicação web (`web`), o banco de dados (`db`) e o agendador de tarefas (`cron`):
   ```bash
   docker compose up --build -d
   ```
3. Rode as migrações para criar a estrutura do banco de dados:
   ```bash
   docker compose exec web python manage.py migrate
   ```
4. Crie um superusuário para acessar o painel de administração (o comando é não-interativo):
   ```bash
   docker compose exec -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_EMAIL=admin@example.com -e DJANGO_SUPERUSER_PASSWORD=admin web python manage.py createsuperuser --no-input
   ```
5. A aplicação estará disponível em `http://localhost:8000`.
   - O painel de administração está em `http://localhost:8000/admin/` (login: `admin`, senha: `admin`).
   - A tela de login para funcionários está em `http://localhost:8000/login/`.

## Próximos Passos e Evolução do Projeto

- **Aprovação de Ponto Fora de Hora:** Implementar o fluxo de solicitação e aprovação para que um funcionário possa bater o ponto fora da janela permitida.
- **Testes Automatizados:** Continuar aumentando a cobertura de testes para garantir a estabilidade das regras de negócio.
- **Melhorias na UI/UX:** Refinar a interface do usuário e a experiência geral, adicionando mais feedback visual e melhorando a navegação.

