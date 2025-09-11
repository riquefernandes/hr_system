# funcionarios/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Funcionario
import random
from datetime import date
from django.contrib.auth.signals import user_logged_in, user_logged_out


@receiver(post_save, sender=Funcionario)
def criar_user_para_funcionario(sender, instance, created, **kwargs):
    if created and not instance.user:
        while True:
            quatro_digitos = random.randint(1000, 9999)
            matricula = f"26{quatro_digitos}"
            if not User.objects.filter(username=matricula).exists():
                break
        ano_atual = date.today().year
        senha = f"{matricula}@Cadastro{ano_atual}"
        nome_completo = instance.nome_completo.lower().split()
        primeiro_nome = nome_completo[0]
        ultimo_nome = nome_completo[-1] if len(nome_completo) > 1 else ""
        email = f"{primeiro_nome}.{ultimo_nome}@suaempresa.com"
        novo_user = User.objects.create_user(
            username=matricula, email=email, password=senha
        )
        instance.user = novo_user
        instance.save()
        print(
            f"Usuário criado para {instance.nome_completo}. Matrícula: {matricula}, Senha: {senha}"
        )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Quando um usuário desloga, marca seu status como Offline."""
    if hasattr(user, "funcionario"):
        user.funcionario.status_operacional = "OFFLINE"
        user.funcionario.save()
