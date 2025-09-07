# Sistema de Administração de RH (hr_system)

## Descrição

**hr_system** é uma aplicação web desenvolvida em Django para a administração de funcionários de um contact center. O sistema permite o cadastro completo de colaboradores, gerenciamento de cargos, centros de custo e bancos, além de um fluxo de trabalho para que os funcionários possam visualizar seus dados e solicitar alterações cadastrais que devem ser aprovadas por um administrador.

A aplicação é totalmente containerizada com Docker, garantindo um ambiente de desenvolvimento e produção consistente e isolado.

## Funcionalidades Implementadas

### Visão do Administrador (Painel `/admin`)
- **CRUD Completo:** Administradores podem Criar, Ler, Atualizar e Deletar registros para:
    - Funcionários
    - Cargos
    - Centros de Custo
    - Bancos
- **Criação Automatizada de Usuários:** Ao criar um novo `Funcionário` no painel de admin, um `User` (login) é criado automaticamente com:
    - **Matrícula:** Gerada no formato `26xxxx` com 4 dígitos aleatórios e únicos.
    - **Senha Provisória:** Gerada no formato `matrícula@CadastroANOATUAL`.
- **Fluxo de Aprovação de Solicitações:**
    - Visualização de solicitações de alteração de endereço e dados bancários.
    - Ações customizadas ("Admin Actions") para aprovar solicitações em lote. A aprovação atualiza automaticamente o cadastro do funcionário e o status da solicitação.
- **Validação de Dados:** O campo CPF possui validação de algoritmo para garantir que apenas CPFs válidos sejam inseridos.
- **Busca por CEP:** A página de cadastro de funcionário possui um script que busca o endereço automaticamente a partir do CEP informado, utilizando a API da ViaCEP.

### Visão do Funcionário Comum (Frontend)
- **Autenticação:** Tela de login (`/login`) e logout (`/logout`) segura, baseada em matrícula e senha.
- **Dashboard Pessoal:** Após o login, o funcionário é direcionado para uma página (`/home`) onde pode visualizar todos os seus dados cadastrais.
- **Solicitação de Alteração:**
    - Formulário dedicado para solicitar alteração de endereço, com busca automática por CEP.
    - Formulário dedicado para solicitar alteração de dados bancários (Banco, Agência e Conta).
    - Histórico de solicitações, exibindo o status de cada uma (Pendente, Aprovado, Recusado).

## Tecnologias Utilizadas

- **Backend:** Python 3.11, Django 5.2
- **Banco de Dados:** PostgreSQL (rodando em Docker)
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla)
- **Framework CSS:** Bootstrap 5 (via CDN para agilidade no desenvolvimento)
- **Ambiente:** Docker, Docker Compose
- **Bibliotecas Python Notáveis:**
    - `psycopg2-binary`: Adaptador para a conexão com o PostgreSQL.
    - `django-localflavor`: Para validação de campos brasileiros, como o CPF.

## Como Rodar o Projeto Localmente

### Pré-requisitos
- Git
- Docker
- Docker Compose

### Passos para Instalação
1. Clone o repositório:
   ```bash
   git clone <URL_DO_SEU_REPOSITORIO>
   cd hr_system
   ```
2. Construa e suba os containers Docker em modo "detached" (background):
   ```bash
   sudo docker compose up --build -d
   ```
3. Rode as migrações para criar a estrutura do banco de dados:
   ```bash
   sudo docker compose exec web python manage.py migrate
   ```
4. Crie um superusuário para acessar o painel de administração:
   ```bash
   sudo docker compose exec web python manage.py createsuperuser
   ```
5. A aplicação estará disponível em `http://localhost:8000`.
   - O painel de administração está em `http://localhost:8000/admin/`.
   - A tela de login para funcionários está em `http://localhost:8000/login/`.

## Próximos Passos e Evolução do Projeto

Com a base atual, o projeto pode evoluir para um sistema de gestão de call center completo, incluindo:
- **Segurança:** Implementar o fluxo de "forçar troca de senha no primeiro acesso".
- **Hierarquia e Permissões:** Criar novos grupos de usuários (Supervisor, Analista de RH) com permissões específicas.
- **Dashboards:** Criar uma visão para o supervisor monitorar o status de sua equipe (logado, em pausa, etc.).
- **Mock de Dados:** Desenvolver um comando de gerenciamento para popular o banco de dados com dados fictícios para testes e simulações.


oi