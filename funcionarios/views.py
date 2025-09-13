# funcionarios/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.views.decorators.http import require_POST
from django.db.models import Sum, Q

# Importações para trabalhar com data e hora
from django.utils import timezone
from datetime import timedelta, datetime

from .forms import (
    SolicitacaoAlteracaoEnderecoForm,
    SolicitacaoAlteracaoBancariaForm,
    SolicitacaoHorarioForm,
)
from .models import (
    SolicitacaoAlteracaoEndereco,
    SolicitacaoAlteracaoBancaria,
    RegistroPonto,
    Funcionario,
    RegraDePausa,
    FuncionarioEscala,
    BancoDeHoras,
    SolicitacaoHorario,
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
    equipe_ids = supervisor_logado.equipe.values_list("id", flat=True)

    # Busca as solicitações pendentes dos funcionários da equipe
    solicitacoes_pendentes = SolicitacaoHorario.objects.filter(
        funcionario_id__in=equipe_ids, status="PENDENTE"
    )

    context = {
        "supervisor": supervisor_logado,
        "solicitacoes_pendentes": solicitacoes_pendentes,
    }
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

    # --- LÓGICA DE DADOS PARA O TEMPLATE ---
    agora = timezone.now()
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_do_dia = agora.replace(hour=23, minute=59, second=59, microsecond=999999)

    # --- LÓGICA DE PAUSAS (ATUALIZADA) ---
    pausas_hoje_count = RegistroPonto.objects.filter(
        funcionario=funcionario,
        tipo="SAIDA_PAUSA",
        timestamp__range=(inicio_do_dia, fim_do_dia),
    ).count()

    proxima_pausa_regra = None
    if funcionario.cargo:
        try:
            # Busca a regra da próxima pausa na sequência
            proxima_pausa_regra = RegraDePausa.objects.get(
                cargo=funcionario.cargo, ordem=pausas_hoje_count + 1
            )
        except RegraDePausa.DoesNotExist:
            proxima_pausa_regra = None  # Não há mais pausas disponíveis

    ultima_pausa = None
    if funcionario.status_operacional == "EM_PAUSA":
        ultima_pausa = (
            RegistroPonto.objects.filter(
                funcionario=funcionario,
                tipo__in=["SAIDA_PAUSA", "SAIDA_ALMOCO"],
                timestamp__range=(inicio_do_dia, fim_do_dia),
            )
            .order_by("-timestamp")
            .first()
        )

    # Lógica de Escala e Banco de Horas
    escala_atual = (
        FuncionarioEscala.objects.filter(
            funcionario=funcionario, data_inicio__lte=agora.date()
        )
        .filter(Q(data_fim__gte=agora.date()) | Q(data_fim__isnull=True))
        .first()
    )

    saldo_total_minutos = (
        BancoDeHoras.objects.filter(funcionario=funcionario).aggregate(
            total=Sum("minutos")
        )["total"]
        or 0
    )
    saldo_horas = int(saldo_total_minutos // 60)
    saldo_minutos_restantes = int(saldo_total_minutos % 60)

    # Lógica de Solicitações
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
        "proxima_pausa_regra": proxima_pausa_regra,  # Variável de contexto atualizada
        "ultima_pausa": ultima_pausa,
        "escala_atual": escala_atual,
        "saldo_banco_horas": f"{saldo_horas}h {saldo_minutos_restantes}min",
        "saldo_banco_horas_negativo": saldo_total_minutos < 0,
    }
    return render(request, "funcionarios/home.html", context)


@login_required
@require_POST
def bate_ponto_view(request):
    funcionario = request.user.funcionario
    tipo_ponto = request.POST.get("tipo_ponto")
    agora = timezone.now()

    if not tipo_ponto:
        messages.error(request, "Você precisa selecionar um tipo de registro.")
        return redirect("funcionarios:home")

    # --- VALIDAÇÃO DE ENTRADA/SAÍDA ÚNICA POR DIA ---
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    if tipo_ponto == "ENTRADA":
        if RegistroPonto.objects.filter(funcionario=funcionario, tipo='ENTRADA', timestamp__gte=inicio_do_dia).exists():
            messages.error(request, "Você já registrou uma entrada hoje.")
            return redirect("funcionarios:home")

    if tipo_ponto == "SAIDA":
        if not RegistroPonto.objects.filter(funcionario=funcionario, tipo='ENTRADA', timestamp__gte=inicio_do_dia).exists():
            messages.error(request, "Você não pode registrar uma saída sem antes registrar uma entrada hoje.")
            return redirect("funcionarios:home")
        if RegistroPonto.objects.filter(funcionario=funcionario, tipo='SAIDA', timestamp__gte=inicio_do_dia).exists():
            messages.error(request, "Você já registrou uma saída hoje.")
            return redirect("funcionarios:home")

    # --- VALIDAÇÃO DE LÓGICA DE PONTO ---

    # Não pode bater ponto se estiver desligado, de férias, etc.
    if funcionario.status != "ATIVO":
        messages.error(request, f"Seu status é '{funcionario.get_status_display()}', você não pode registrar o ponto.")
        return redirect("funcionarios:home")

    # Validações de Entrada
    if tipo_ponto == "ENTRADA":
        if funcionario.status_operacional != "OFFLINE":
            messages.error(request, f"Ação inválida. Seu status atual é '{funcionario.get_status_operacional_display()}'.")
            return redirect("funcionarios:home")
        
        data_local = timezone.localtime(agora).date()
        solicitacao_aprovada = SolicitacaoHorario.objects.filter(
            funcionario=funcionario, status="APROVADO", data_hora_ponto__date=data_local
        ).exists()
        if not solicitacao_aprovada:
            escala_atual = FuncionarioEscala.objects.filter(
                funcionario=funcionario, data_inicio__lte=data_local
            ).filter(Q(data_fim__gte=data_local) | Q(data_fim__isnull=True)).first()
            if not escala_atual:
                messages.error(request, "Você não tem uma escala de trabalho definida. Contate o RH.")
                return redirect("funcionarios:home")
            # ... (resto da lógica de janela de horário)

    # Validações de Pausa
    if tipo_ponto == "SAIDA_PAUSA":
        if funcionario.status_operacional != "DISPONIVEL":
            messages.error(request, f"Você só pode iniciar uma pausa se estiver 'Disponível'.")
            return redirect("funcionarios:home")

        # Validação da regra de pausa sequencial
        inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
        pausas_hoje_count = RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="SAIDA_PAUSA", timestamp__gte=inicio_do_dia
        ).count()
        
        try:
            # Apenas verifica se a próxima regra existe. Não precisa usar a variável.
            RegraDePausa.objects.get(cargo=funcionario.cargo, ordem=pausas_hoje_count + 1)
        except RegraDePausa.DoesNotExist:
            messages.error(request, "Você não tem mais pausas disponíveis ou elas não estão configuradas para seu cargo.")
            return redirect("funcionarios:home")

    if tipo_ponto == "VOLTA_PAUSA":
        if funcionario.status_operacional != "EM_PAUSA":
            messages.error(request, f"Você só pode voltar de uma pausa se estiver 'Em Pausa'.")
            return redirect("funcionarios:home")

    # Validações de Saída
    if tipo_ponto == "SAIDA":
        if funcionario.status_operacional not in ["DISPONIVEL", "EM_PAUSA"]:
            messages.error(request, f"Você não pode registrar a saída com o status '{funcionario.get_status_operacional_display()}'.")
            return redirect("funcionarios:home")

    # --- FIM DA VALIDAÇÃO ---

    # Mapeia o tipo de ponto para o novo status
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
    messages.success(request, f"'{tipo_ponto.replace('_', ' ').title()}' registrada com sucesso!")
    return redirect("funcionarios:home")


@login_required
def solicitar_horario_view(request):
    if request.method == "POST":
        form = SolicitacaoHorarioForm(request.POST)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.funcionario = request.user.funcionario
            solicitacao.data_hora_ponto = timezone.now()
            solicitacao.save()
            messages.success(
                request, "Sua solicitação foi enviada ao seu supervisor para análise."
            )
            return redirect("funcionarios:home")
    else:
        form = SolicitacaoHorarioForm()

    context = {"form": form}
    return render(request, "funcionarios/solicitar_horario.html", context)


# --- NOVA VIEW PARA SERVIR A TABELA VIA HTMX ---
@login_required
def tabela_equipe_view(request):
    supervisor = request.user.funcionario
    equipe = supervisor.equipe.all()
    agora = timezone.now()
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    for membro in equipe:
        membro.ultima_pausa = None
        membro.limite_pausa_segundos = 0

        if membro.status_operacional == "EM_PAUSA":
            ultima_pausa_registro = (
                RegistroPonto.objects.filter(
                    funcionario=membro, tipo__in=["SAIDA_PAUSA", "SAIDA_ALMOCO"]
                )
                .order_by("-timestamp")
                .first()
            )
            membro.ultima_pausa = ultima_pausa_registro

            if ultima_pausa_registro and ultima_pausa_registro.tipo == "SAIDA_PAUSA":
                pausas_hoje_count = RegistroPonto.objects.filter(
                    funcionario=membro,
                    tipo="SAIDA_PAUSA",
                    timestamp__gte=inicio_do_dia,
                ).count()
                regra_atual = RegraDePausa.objects.filter(
                    cargo=membro.cargo, ordem=pausas_hoje_count
                ).first()
                if regra_atual:
                    membro.limite_pausa_segundos = regra_atual.duracao_minutos * 60

        membro.escala_atual = (
            FuncionarioEscala.objects.filter(
                funcionario=membro, data_inicio__lte=agora.date()
            )
            .filter(Q(data_fim__gte=agora.date()) | Q(data_fim__isnull=True))
            .first()
        )

    return render(request, "funcionarios/_tabela_equipe.html", {"equipe": equipe})


def logout_view(request):
    logout(request)
    return redirect("funcionarios:login")


@login_required
def aprovar_solicitacao_horario(request, pk):
    solicitacao = get_object_or_404(SolicitacaoHorario, pk=pk)
    supervisor = request.user.funcionario

    # Garante que apenas o supervisor direto do funcionário pode aprovar
    if solicitacao.funcionario.supervisor == supervisor:
        solicitacao.status = "APROVADO"
        solicitacao.analisado_por = supervisor
        solicitacao.data_analise = timezone.now()
        solicitacao.save()
        messages.success(request, "A solicitação foi aprovada com sucesso.")
    else:
        messages.error(request, "Você não tem permissão para aprovar esta solicitação.")

    return redirect("funcionarios:supervisor_dashboard")


@login_required
def recusar_solicitacao_horario(request, pk):
    solicitacao = get_object_or_404(SolicitacaoHorario, pk=pk)
    supervisor = request.user.funcionario

    # Garante que apenas o supervisor direto do funcionário pode recusar
    if solicitacao.funcionario.supervisor == supervisor:
        solicitacao.status = "RECUSADO"
        solicitacao.analisado_por = supervisor
        solicitacao.data_analise = timezone.now()
        solicitacao.save()
        messages.success(request, "A solicitação foi recusada.")
    else:
        messages.error(request, "Você não tem permissão para recusar esta solicitação.")

    return redirect("funcionarios:supervisor_dashboard")
