# Sistema de Gestão de RH (hr_system)

## Descrição

**hr_system** é uma aplicação web desenvolvida em Django para a administração de funcionários de um contact center. O sistema evoluiu para incluir um robusto controle de jornada de trabalho, com registro de ponto, gerenciamento de escalas, banco de horas, relatórios e dashboards para supervisores **e Analistas de RH**.

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
- **Página Inicial (`/home`) - Simplificada:**
    - Foco exclusivo no **Registro de Ponto Virtual:** Funcionalidade para registrar Entrada, Saída e Pausas (programadas e pessoais).
    - **Contagem Regressiva:** Exibe o tempo restante de pausas programadas.
    - **Tempo Logado:** Exibe o tempo que o funcionário está logado desde a última entrada.
    - **Últimos Registros:** Tabela com os últimos registros de ponto do dia.
- **Meu Perfil (`/meu-perfil`) - Nova Página:**
    - Visualização completa de dados cadastrais (pessoais, endereço, bancários).
    - Formulários para **Solicitação de Alteração de Endereço e Dados Bancários**, com histórico e status.
    - Histórico de **Solicitações de Abono** enviadas.
- **Minha Jornada (`/minha-jornada`) - Nova Página:**
    - Detalhes da **Escala de Trabalho** atual do funcionário (horários, dias).
    - Visualização do **Saldo do Banco de Horas** total.
    - Link para o Relatório de Folha de Ponto individual.
- **Navegação Centralizada:** Um menu de navegação responsivo (hamburger menu) foi adicionado à base da aplicação, facilitando o acesso a todas as páginas.

### Visão do Supervisor / Analista de RH

- **Dashboard de Gestão (`/supervisor/dashboard`):**
    - Visualização em tempo real do status operacional de todos os funcionários da sua equipe (Disponível, Em Pausa, Offline).
    - **Para Analistas de RH:** Acesso a todas as solicitações pendentes de **todos os funcionários** (horário e abono).
    - **Para Supervisores:** Acesso a todas as solicitações pendentes de sua equipe.
    - A tabela da equipe é atualizada automaticamente a cada 15 segundos (via HTMX).
    - **Cronômetro de Pausa:** Exibe há quanto tempo um funcionário está em pausa.
    - **Alerta de Limite de Pausa:** O cronômetro fica vermelho e em negrito se o funcionário exceder o tempo limite para aquela pausa específica.
- **Relatório de Equipe (`/relatorio/equipe`):**
    - Permite que o supervisor ou Analista de RH gere um relatório consolidado para sua equipe/empresa dentro de um período de datas.
    - O relatório exibe o total de horas extras, horas devidas e faltas injustificadas para cada membro da equipe e também os totais gerais.
- **Aprovação de Solicitações:** Supervisores e Analistas de RH podem aprovar/recusar solicitações de horário e abono.

### Motor de Processamento (Backend)

- **Cálculo de Banco de Horas Automatizado:** Um comando de gerenciamento (`processar_pontos`) é executado diariamente (agora a cada 2 minutos para testes) por um **job agendado (cron)** dentro de um container Docker dedicado. Ele analisa os registros de ponto do dia anterior, compara com a escala do funcionário e calcula o saldo de horas (atrasos, saídas antecipadas, horas extras), registrando tudo na tabela de `BancoDeHoras`.
- **Integridade de Dados:** O modelo `BancoDeHoras` agora possui uma restrição de unicidade (`unique_together`) para evitar a criação de registros duplicados para o mesmo funcionário no mesmo dia. Um script de migração de dados foi adicionado para limpar duplicatas existentes.
- **Lógica de Abono Aprimorada:** O script `processar_pontos` agora ignora dias com `SolicitacaoAbono` aprovada, garantindo que o saldo de horas do dia seja zero (nem débito, nem crédito indevido).

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
2. **Remova o ambiente virtual local (se existir), pois ele agora é gerenciado pelo Docker:**
    ```bash
    rm -rf venv
    ```
3. Construa e suba os containers Docker em modo "detached" (background). O compose agora inclui o serviço da aplicação web (`web`), o banco de dados (`db`) e o agendador de tarefas (`cron`):
    ```bash
    docker compose up --build -d
    ```
4. Rode as migrações para criar a estrutura do banco de dados:
    ```bash
    docker compose exec web python manage.py migrate
    ```
5. Crie um superusuário para acessar o painel de administração (o comando é não-interativo):
    ```bash
    docker compose exec -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_EMAIL=admin@example.com -e DJANGO_SUPERUSER_PASSWORD=admin web python manage.py createsuperuser --no-input
    ```
6. A aplicação estará disponível em `http://localhost:8000`.
    - O painel de administração está em `http://localhost:8000/admin/` (login: `admin`, senha: `admin`).
    - A tela de login para funcionários está em `http://localhost:8000/login/`.

## Próximos Passos e Evolução do Projeto

- **Aprovação de Ponto Fora de Hora:** Implementar o fluxo de solicitação e aprovação para que um funcionário possa bater o ponto fora da janela permitida.
- **Testes Automatizados:** Continuar aumentando a cobertura de testes para garantir a estabilidade das regras de negócio.
- **Melhorias na UI/UX:** Refinar a interface do usuário e a experiência geral, adicionando mais feedback visual e melhorando a navegação.
- **Reintrodução da pausa para almoço:** Integrar a pausa para almoço de forma robusta na lógica de controle de ponto e na UI.
- **Gestão de Feriados:** Adicionar funcionalidade para o sistema reconhecer e aplicar regras específicas em feriados.
