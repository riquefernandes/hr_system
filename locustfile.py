# locustfile.py
from locust import HttpUser, task, between


class FuncionarioUser(HttpUser):
    host = "http://web:8000"
    # Simula um usuário que espera entre 1 e 3 segundos entre cada ação
    wait_time = between(1, 3)

    def on_start(self):
        """
        Esta função é executada uma vez quando um usuário virtual "nasce".
        Vamos usá-la para fazer o login.
        """
        # --- ATENÇÃO: SUBSTITUA COM OS DADOS DO SEU USUÁRIO DE TESTE ---
        matricula = "265476"
        senha = "376895He@"
        # -----------------------------------------------------------

        # Pega o token CSRF da página de login primeiro
        response = self.client.get("/login/")
        csrf_token = response.cookies["csrftoken"]

        # Envia os dados de login como se estivesse preenchendo o formulário
        self.client.post(
            "/login/",
            {
                "username": matricula,
                "password": senha,
                "csrfmiddlewaretoken": csrf_token,
            },
            headers={"X-CSRFToken": csrf_token},
        )

    @task  # Tarefa principal que o usuário ficará repetindo
    def view_home(self):
        """Acessa a página home repetidamente."""
        self.client.get("/home/")

    @task(3)  # Tarefa secundária, executada 3x mais que a principal
    def view_dashboard(self):
        """Acessa o dashboard do supervisor repetidamente."""
        # Mesmo que o usuário não seja supervisor, podemos testar o acesso.
        # A view vai redirecioná-lo, o que também é uma carga para o servidor.
        self.client.get("/supervisor/dashboard/")

