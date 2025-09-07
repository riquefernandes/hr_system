# funcionarios/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Funcionario

# Novas importações necessárias
import random
from datetime import date


@receiver(post_save, sender=Funcionario)
def criar_user_para_funcionario(sender, instance, created, **kwargs):
    # A lógica só roda se um NOVO funcionário for criado E se ele ainda não tiver um user
    if created and not instance.user:

        # --- NOVA LÓGICA DA MATRÍCULA ---
        while True:
            # Gera 4 números aleatórios entre 1000 e 9999
            quatro_digitos = random.randint(1000, 9999)
            matricula = f"26{quatro_digitos}"
            # Garante que a matrícula não exista antes de continuar
            if not User.objects.filter(username=matricula).exists():
                break  # Sai do loop se a matrícula for única

        # --- NOVA LÓGICA DA SENHA ---
        ano_atual = date.today().year
        senha = f"{matricula}@Cadastro{ano_atual}"

        # Lógica do email (continua a mesma)
        nome_completo = instance.nome_completo.lower().split()
        primeiro_nome = nome_completo[0]
        ultimo_nome = nome_completo[-1] if len(nome_completo) > 1 else ""
        email = f"{primeiro_nome}.{ultimo_nome}@suaempresa.com"

        # Cria o objeto User com os novos dados
        novo_user = User.objects.create_user(
            username=matricula, email=email, password=senha
        )

        # Liga o User recém-criado ao Funcionario e salva
        instance.user = novo_user
        instance.save()

        # Mensagem de log atualizada para debug
        print(
            f"Usuário criado para {instance.nome_completo}. Matrícula: {matricula}, Senha: {senha}, email: {email}"
        )
