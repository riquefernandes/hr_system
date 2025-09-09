# funcionarios/models.py (VERSÃO COMPLETA E FINAL)
from django.db import models
from django.contrib.auth.models import User
from localflavor.br.models import BRCPFField

# --- Modelos de Apoio (Definidos Primeiro) ---


class Cargo(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class CentroDeCusto(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Banco(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


# --- Modelo Principal ---


class Funcionario(models.Model):
    SEXO_CHOICES = [
        ("M", "Masculino"),
        ("F", "Feminino"),
        ("O", "Outro"),
        ("N", "Prefiro não dizer"),
    ]

    # Campos de Login e Pessoais
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome_completo = models.CharField(max_length=255)
    deve_alterar_senha = models.BooleanField(default=True)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)

    # Campos de Endereço Estruturado
    cep = models.CharField(max_length=9)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    complemento = models.CharField(max_length=100, blank=True, null=True)

    # Campos de Documentos
    cpf = BRCPFField(unique=True)
    rg = models.CharField(max_length=12)

    # Campos de Trabalho
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True)
    centro_de_custo = models.ForeignKey(
        CentroDeCusto, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Campos Bancários
    banco = models.ForeignKey(Banco, on_delete=models.SET_NULL, null=True, blank=True)
    agencia = models.CharField(max_length=10)
    conta = models.CharField(max_length=15)

    def __str__(self):
        return self.nome_completo


# --- Modelos de Solicitações ---


class SolicitacaoAlteracaoEndereco(models.Model):
    STATUS_CHOICES = [("P", "Pendente"), ("A", "Aprovado"), ("R", "Recusado")]

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    cep = models.CharField(max_length=9)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P")
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Solicitação de Endereço de {self.funcionario.nome_completo}"


class SolicitacaoAlteracaoBancaria(models.Model):
    STATUS_CHOICES = [("P", "Pendente"), ("A", "Aprovado"), ("R", "Recusado")]

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    banco = models.ForeignKey(Banco, on_delete=models.SET_NULL, null=True)
    agencia = models.CharField(max_length=10)
    conta = models.CharField(max_length=15)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P")
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Solicitação Bancária de {self.funcionario.nome_completo}"
