# funcionarios/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.views.decorators.http import require_POST

# Importações para trabalhar com data e hora
from django.utils import timezone
from datetime import timedelta

from .forms import SolicitacaoAlteracaoEnderecoForm, SolicitacaoAlteracaoBancariaForm
from .models import (
    SolicitacaoAlteracaoEndereco,
    SolicitacaoAlteracaoBancaria,
    RegistroPonto,
    Funcionario,
)


def login_view(request):
    if request.method == "POST":
        matricula = request.POST.get("username")
        senha = request.POST.get("password")
        user = authenticate(request, username=matricula, password=senha)
        if user is not None:
            login(request, user)
            return redirect("funcionarios:home")
        else:
            messages.error(request, "Matrícula ou senha incorreta. Tente novamente.")
            return render(request, "funcionarios/login.html")
    else:
        return render(request, "funcionarios/login.html")


class CustomPasswordChangeView(PasswordChangeView):
    def form_valid(self, form):
        funcionario = self.request.user.funcionario
        funcionario.deve_alterar_senha = False
        funcionario.save()
        return super().form_valid(form)


@login_required
def supervisor_dashboard_view(request):
    if (
        not request.user.has_perm("funcionarios.view_funcionario")
        and not request.user.is_superuser
    ):
        return redirect("funcionarios:home")

    supervisor_logado = request.user.funcionario
    equipe_do_supervisor = supervisor_logado.equipe.all()

    context = {"supervisor": supervisor_logado, "equipe": equipe_do_supervisor}
    return render(request, "funcionarios/supervisor_dashboard.html", context)


@login_required
def home_view(request):
    funcionario = request.user.funcionario
    form_endereco = SolicitacaoAlteracaoEnderecoForm()
    form_bancario = SolicitacaoAlteracaoBancariaForm()

    if request.method == "POST":
        if "submit_endereco" in request.POST:
            form_endereco = SolicitacaoAlteracaoEnderecoForm(request.POST)
            if form_endereco.is_valid():
                solicitacao = form_endereco.save(commit=False)
                solicitacao.funcionario = funcionario
                solicitacao.save()
                messages.success(
                    request,
                    "Sua solicitação de alteração de endereço foi enviada para aprovação!",
                )
                return redirect("funcionarios:home")
        elif "submit_bancario" in request.POST:
            form_bancario = SolicitacaoAlteracaoBancariaForm(request.POST)
            if form_bancario.is_valid():
                solicitacao = form_bancario.save(commit=False)
                solicitacao.funcionario = funcionario
                solicitacao.save()
                messages.success(
                    request,
                    "Sua solicitação de alteração bancária foi enviada para aprovação!",
                )
                return redirect("funcionarios:home")

    hoje = timezone.now().date()
    pausas_hoje_count = 0
    regras_cargo = funcionario.cargo

    if regras_cargo:
        pausas_hoje_count = RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="SAIDA_PAUSA", timestamp__date=hoje
        ).count()

    solicitacoes_endereco = SolicitacaoAlteracaoEndereco.objects.filter(
        funcionario=funcionario
    ).order_by("-data_solicitacao")
    solicitacoes_bancarias = SolicitacaoAlteracaoBancaria.objects.filter(
        funcionario=funcionario
    ).order_by("-data_solicitacao")

    context = {
        "funcionario_data": funcionario,
        "form_endereco": form_endereco,
        "form_bancario": form_bancario,
        "solicitacoes_endereco": solicitacoes_endereco,
        "solicitacoes_bancarias": solicitacoes_bancarias,
        "pausas_hoje_count": pausas_hoje_count,
        "regras_cargo": regras_cargo,
    }
    return render(request, "funcionarios/home.html", context)


@login_required
@require_POST
def bate_ponto_view(request):
    funcionario = request.user.funcionario
    tipo_ponto = request.POST.get("tipo_ponto")

    if not tipo_ponto:
        messages.error(request, "Você precisa selecionar um tipo de registro.")
        return redirect("funcionarios:home")

    if tipo_ponto == "SAIDA_PAUSA":
        regras_cargo = funcionario.cargo
        hoje = timezone.now().date()

        if not regras_cargo:
            messages.error(
                request,
                "Não foi possível verificar as regras de pausa (cargo não definido).",
            )
            return redirect("funcionarios:home")

        pausas_hoje = RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="SAIDA_PAUSA", timestamp__date=hoje
        ).count()

        if pausas_hoje >= regras_cargo.max_pausas_diarias:
            messages.error(
                request,
                f"Você já atingiu o limite de {regras_cargo.max_pausas_diarias} pausas por dia.",
            )
            return redirect("funcionarios:home")

        registros_pausa_hoje = RegistroPonto.objects.filter(
            funcionario=funcionario,
            tipo__in=["SAIDA_PAUSA", "VOLTA_PAUSA"],
            timestamp__date=hoje,
        ).order_by("timestamp")

        duracao_total_pausas = timedelta()
        ultimo_inicio_pausa = None

        for registro in registros_pausa_hoje:
            if registro.tipo == "SAIDA_PAUSA":
                ultimo_inicio_pausa = registro.timestamp
            elif registro.tipo == "VOLTA_PAUSA" and ultimo_inicio_pausa:
                duracao_total_pausas += registro.timestamp - ultimo_inicio_pausa
                ultimo_inicio_pausa = None

        if (
            duracao_total_pausas.total_seconds() / 60
            >= regras_cargo.duracao_max_pausas_minutos
        ):
            messages.error(
                request,
                f"Você já atingiu o tempo limite de {regras_cargo.duracao_max_pausas_minutos} minutos em pausas hoje.",
            )
            return redirect("funcionarios:home")

    status_map = {
        "ENTRADA": "DISPONIVEL",
        "SAIDA_PAUSA": "EM_PAUSA",
        "VOLTA_PAUSA": "DISPONIVEL",
        "SAIDA_ALMOCO": "EM_PAUSA",
        "VOLTA_ALMOCO": "DISPONIVEL",
        "SAIDA": "OFFLINE",
    }

    funcionario.status_operacional = status_map.get(
        tipo_ponto, funcionario.status_operacional
    )
    funcionario.save()

    RegistroPonto.objects.create(funcionario=funcionario, tipo=tipo_ponto)
    messages.success(request, "Ponto registrado com sucesso!")
    return redirect("funcionarios:home")


def logout_view(request):
    logout(request)
    return redirect("funcionarios:login")


# --- NOVA VIEW PARA SERVIR A TABELA VIA HTMX ---
@login_required
def tabela_equipe_view(request):
    supervisor = request.user.funcionario
    equipe = supervisor.equipe.all()
    return render(request, "funcionarios/_tabela_equipe.html", {"equipe": equipe})
