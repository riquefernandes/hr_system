# funcionarios/tests.py
from django.test import TestCase
from django.urls import reverse

# Importações para os modelos que vamos criar
from django.contrib.auth.models import User
from .models import Funcionario, Cargo, CentroDeCusto, Banco


class PaginasDoSistemaTests(TestCase):

    def test_pagina_login_carrega_corretamente(self):
        """
        Verifica se a página de login responde com o status code 200 (OK).
        """
        url = reverse("funcionarios:login")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "funcionarios/login.html")

    def test_pagina_home_redireciona_se_nao_estiver_logado(self):
        """
        Verifica se a página home, que é protegida, redireciona (status 302)
        se um usuário não logado tentar acessá-la.
        """
        url = reverse("funcionarios:home")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("funcionarios:login") + "?next=" + url)

    def test_pagina_home_mostra_dados_do_usuario_logado(self):
        """
        Verifica se, após o login, os dados do funcionário aparecem na página home.
        """
        # PASSO 1: Preparação - Crie todos os dados necessários no BD de teste
        cargo_teste = Cargo.objects.create(nome="Cargo de Teste")
        banco_teste = Banco.objects.create(nome="Banco de Teste")
        cc_teste = CentroDeCusto.objects.create(nome="CC de Teste")

        usuario_teste = User.objects.create_user(
            username="269999", password="senha_super_secreta"
        )

        funcionario_teste = Funcionario.objects.create(
            user=usuario_teste,
            nome_completo="Nome Completo do Funcionário de Teste",
            data_nascimento="1990-01-01",
            sexo="O",
            cpf="111.444.777-05",  # CPF válido
            rg="12345678",
            cep="01001-000",
            rua="Praça da Sé",
            numero="1",
            bairro="Sé",
            cidade="São Paulo",
            estado="SP",
            data_contratacao="2025-01-01",
            cargo=cargo_teste,
            banco=banco_teste,
            centro_de_custo=cc_teste,
            agencia="0001",
            conta="12345-6",
        )

        # --- CORREÇÃO APLICADA AQUI ---
        # Simula que o usuário já alterou a senha uma vez
        funcionario_teste.deve_alterar_senha = False
        funcionario_teste.save()
        # --------------------------------

        # PASSO 2: Ação - Simule o login
        self.client.login(username="269999", password="senha_super_secreta")

        # PASSO 3: Ação - Acesse a página home
        url = reverse("funcionarios:home")
        response = self.client.get(url)

        # PASSO 4: Verificações (Asserts)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nome Completo do Funcionário de Teste")
        self.assertContains(response, "111.444.777-05")
