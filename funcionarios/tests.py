# funcionarios/tests.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta, datetime

# Importações para os modelos que vamos criar
from django.contrib.auth.models import User
from .models import Funcionario, Cargo, CentroDeCusto, Banco, Escala, FuncionarioEscala, BancoDeHoras, RegistroPonto


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

    def test_pagina_home_mostra_nome_do_usuario_logado(self):
        """
        Verifica se, após o login, o nome do funcionário aparece na página home.
        """
        # Preparação
        usuario_teste = User.objects.create_user(username="269999", password="senha_super_secreta")
        funcionario_teste = Funcionario.objects.create(
            user=usuario_teste,
            nome_completo="Nome Completo do Funcionário de Teste",
            cpf="111.444.777-05",
            data_nascimento="1990-01-01",
            data_contratacao="2025-01-01",
            deve_alterar_senha=False
        )

        # Ação
        self.client.login(username="269999", password="senha_super_secreta")
        url = reverse("funcionarios:home")
        response = self.client.get(url)

        # Verificação
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nome Completo do Funcionário de Teste")

    def test_pagina_meu_perfil_mostra_dados_do_usuario_logado(self):
        """
        Verifica se, após o login, os dados do funcionário aparecem na página Meu Perfil.
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

        # PASSO 3: Ação - Acesse a página Meu Perfil
        url = reverse("funcionarios:meu_perfil")
        response = self.client.get(url)

        # PASSO 4: Verificações (Asserts)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nome Completo do Funcionário de Teste")
        self.assertContains(response, "111.444.777-05")


class RelatorioEquipeViewTests(TestCase):
    def setUp(self):
        # Criar escala
        self.escala = Escala.objects.create(
            nome="Escala Teste",
            dias_semana="0,1,2,3,4",  # Seg a Sex
            horario_entrada="09:00",
            horario_saida="18:00",
        )

        # Criar supervisor
        self.supervisor_user = User.objects.create_user('supervisor', 'sup@test.com', 'password')
        self.supervisor = Funcionario.objects.create(
            user=self.supervisor_user,
            nome_completo="Supervisor Teste",
            cpf="11111111111",
            data_nascimento='1980-01-01',
            data_contratacao='2020-01-01',
            deve_alterar_senha=False,
        )

        # Criar membro da equipe 1
        self.membro1_user = User.objects.create_user('membro1', 'm1@test.com', 'password')
        self.membro1 = Funcionario.objects.create(
            user=self.membro1_user,
            nome_completo="Membro Equipe 1",
            cpf="22222222222",
            data_nascimento='1900-01-01',
            data_contratacao='2021-01-01',
            supervisor=self.supervisor,
            deve_alterar_senha=False,
        )
        FuncionarioEscala.objects.create(funcionario=self.membro1, escala=self.escala, data_inicio='2021-01-01')

        # Criar membro da equipe 2
        self.membro2_user = User.objects.create_user('membro2', 'm2@test.com', 'password')
        self.membro2 = Funcionario.objects.create(
            user=self.membro2_user,
            nome_completo="Membro Equipe 2",
            cpf="33333333333",
            data_nascimento='1992-01-01',
            data_contratacao='2021-01-01',
            supervisor=self.supervisor,
            deve_alterar_senha=False,
        )
        FuncionarioEscala.objects.create(funcionario=self.membro2, escala=self.escala, data_inicio='2021-01-01')

        # Criar dados de teste para o período
        self.data_inicio = date.today() - timedelta(days=10)
        self.data_fim = date.today()

        # Dados para membro 1: 2h extras, 30m devidos, 1 falta
        BancoDeHoras.objects.create(funcionario=self.membro1, data=self.data_inicio, minutos=120, descricao="Horas extras")
        BancoDeHoras.objects.create(funcionario=self.membro1, data=self.data_inicio + timedelta(days=1), minutos=-30, descricao="Atraso")
        # A falta será calculada (não criar registro de ponto em um dia de trabalho)

        # Dados para membro 2: 1h extra
        BancoDeHoras.objects.create(funcionario=self.membro2, data=self.data_inicio, minutos=60, descricao="Horas extras")
        # Criar um registro de ponto para o membro 2 para não contar como falta
        # Adicionando registros para todos os dias úteis para o membro 2
        for i in range((self.data_fim - self.data_inicio).days + 1):
            data_atual = self.data_inicio + timedelta(days=i)
            if data_atual.weekday() < 5: # Se for dia de semana
                timestamp_aware = timezone.make_aware(datetime.combine(data_atual, datetime.min.time()))
                RegistroPonto.objects.create(funcionario=self.membro2, timestamp=timestamp_aware, tipo='ENTRADA')


    def test_acesso_negado_para_nao_supervisor(self):
        self.client.login(username='membro1', password='password')
        response = self.client.get(reverse('funcionarios:relatorio_equipe'))
        # Como a view agora redireciona para 'home', o status é 302
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('funcionarios:home'))

    def test_acesso_permitido_para_supervisor(self):
        self.client.login(username='supervisor', password='password')
        response = self.client.get(reverse('funcionarios:relatorio_equipe'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'funcionarios/relatorio_equipe.html')

    def test_calculo_do_relatorio(self):
        self.client.login(username='supervisor', password='password')
        response = self.client.post(reverse('funcionarios:relatorio_equipe'), {
            'data_inicio': self.data_inicio.strftime('%Y-%m-%d'),
            'data_fim': self.data_fim.strftime('%Y-%m-%d'),
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('relatorio', response.context)
        self.assertIn('totais', response.context)

        relatorio = response.context['relatorio']
        totais = response.context['totais']

        # Checar dados do membro 1
        dados_membro1 = next(item for item in relatorio if item['funcionario'] == self.membro1)
        self.assertEqual(dados_membro1['horas_extras_minutos'], 120)
        self.assertEqual(dados_membro1['horas_devidas_minutos'], 30)
        self.assertGreater(dados_membro1['faltas'], 0)

        # Checar dados do membro 2
        dados_membro2 = next(item for item in relatorio if item['funcionario'] == self.membro2)
        self.assertEqual(dados_membro2['horas_extras_minutos'], 60)
        self.assertEqual(dados_membro2['horas_devidas_minutos'], 0)
        self.assertEqual(dados_membro2['faltas'], 0)

        # Checar totais
        self.assertEqual(totais['total_geral_extras_minutos'], 180)
        self.assertEqual(totais['total_geral_devidas_minutos'], 30)
        self.assertEqual(totais['total_geral_faltas'], dados_membro1['faltas'])
