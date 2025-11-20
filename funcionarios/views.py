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
from datetime import timedelta, datetime, time
from collections import defaultdict


from .forms import (
    RelatorioFolhaPontoForm,
    RelatorioEquipeForm,
    SolicitacaoAbonoForm,
    SolicitacaoAlteracaoEnderecoForm,
    SolicitacaoAlteracaoBancariaForm,
    SolicitacaoHorarioForm,
)
from .models import (
    SolicitacaoAbono,
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
    user = request.user
    if not user.is_superuser and not user.has_perm("funcionarios.view_funcionario"):
        return redirect("funcionarios:home")

    is_analista_rh = user.groups.filter(name='Analista de RH').exists()
    
    solicitacoes_horario_pendentes = SolicitacaoHorario.objects.filter(status="PENDENTE")
    solicitacoes_abono_pendentes = SolicitacaoAbono.objects.filter(status="PENDENTE")

    if not is_analista_rh:
        supervisor_logado = user.funcionario
        equipe_ids = supervisor_logado.equipe.values_list("id", flat=True)
        solicitacoes_horario_pendentes = solicitacoes_horario_pendentes.filter(
            funcionario_id__in=equipe_ids
        )
        solicitacoes_abono_pendentes = solicitacoes_abono_pendentes.filter(
            funcionario_id__in=equipe_ids
        )

    context = {
        "supervisor": user.funcionario,
        "solicitacoes_horario_pendentes": solicitacoes_horario_pendentes,
        "solicitacoes_abono_pendentes": solicitacoes_abono_pendentes,
    }
    return render(request, "funcionarios/supervisor_dashboard.html", context)


@login_required
def home_view(request):
    funcionario = request.user.funcionario
    agora = timezone.now()
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_do_dia = agora.replace(hour=23, minute=59, second=59, microsecond=999999)

    pausas_hoje_count = RegistroPonto.objects.filter(
        funcionario=funcionario,
        tipo="SAIDA_PAUSA",
        timestamp__range=(inicio_do_dia, fim_do_dia),
    ).count()

    proxima_pausa_regra = None
    if funcionario.cargo:
        try:
            proxima_pausa_regra = RegraDePausa.objects.get(
                cargo=funcionario.cargo, ordem=pausas_hoje_count + 1
            )
        except RegraDePausa.DoesNotExist:
            proxima_pausa_regra = None

    ultima_pausa = None
    hora_fim_pausa = None
    if funcionario.status_operacional == "EM_PAUSA":
        ultima_pausa = (
            RegistroPonto.objects.filter(
                funcionario=funcionario,
                tipo__in=["SAIDA_PAUSA", "SAIDA_ALMOCO", "SAIDA_PAUSA_PESSOAL"],
                timestamp__range=(inicio_do_dia, fim_do_dia),
            )
            .order_by("-timestamp")
            .first()
        )
        if ultima_pausa and ultima_pausa.tipo == "SAIDA_PAUSA" and funcionario.cargo:
            try:
                regra_pausa_atual = RegraDePausa.objects.get(
                    cargo=funcionario.cargo, ordem=pausas_hoje_count
                )
                hora_fim_pausa = ultima_pausa.timestamp + timedelta(
                    minutes=regra_pausa_atual.duracao_minutos
                )
            except RegraDePausa.DoesNotExist:
                pass

    ultimo_ponto_entrada = RegistroPonto.objects.filter(
        funcionario=funcionario,
        tipo='ENTRADA',
        timestamp__date=agora.date()
    ).order_by('-timestamp').first()

    context = {
        "funcionario_data": funcionario,
        "proxima_pausa_regra": proxima_pausa_regra,
        "ultima_pausa": ultima_pausa,
        "hora_fim_pausa": hora_fim_pausa.isoformat() if hora_fim_pausa else None,
        "ultimo_ponto_entrada": ultimo_ponto_entrada,
    }
    return render(request, "funcionarios/home.html", context)


@login_required
def meu_perfil_view(request):
    funcionario = request.user.funcionario
    form_endereco = SolicitacaoAlteracaoEnderecoForm(instance=funcionario)
    form_bancario = SolicitacaoAlteracaoBancariaForm(instance=funcionario)

    if request.method == "POST":
        if "submit_endereco" in request.POST:
            form_endereco = SolicitacaoAlteracaoEnderecoForm(request.POST, instance=funcionario)
            if form_endereco.is_valid():
                solicitacao, created = SolicitacaoAlteracaoEndereco.objects.update_or_create(
                    funcionario=funcionario, status='P',
                    defaults=form_endereco.cleaned_data
                )
                if created:
                    messages.success(request, "Sua solicitação de alteração de endereço foi enviada!")
                else:
                    messages.warning(request, "Você já tem uma solicitação de endereço pendente. Atualizamos com os novos dados.")
                return redirect("funcionarios:meu_perfil")
        elif "submit_bancario" in request.POST:
            form_bancario = SolicitacaoAlteracaoBancariaForm(request.POST, instance=funcionario)
            if form_bancario.is_valid():
                solicitacao, created = SolicitacaoAlteracaoBancaria.objects.update_or_create(
                    funcionario=funcionario, status='P',
                    defaults=form_bancario.cleaned_data
                )
                if created:
                    messages.success(request, "Sua solicitação de alteração bancária foi enviada!")
                else:
                    messages.warning(request, "Você já tem uma solicitação bancária pendente. Atualizamos com os novos dados.")
                return redirect("funcionarios:meu_perfil")

    solicitacoes_endereco = SolicitacaoAlteracaoEndereco.objects.filter(funcionario=funcionario).order_by("-data_solicitacao")
    solicitacoes_bancarias = SolicitacaoAlteracaoBancaria.objects.filter(funcionario=funcionario).order_by("-data_solicitacao")
    solicitacoes_abono = SolicitacaoAbono.objects.filter(funcionario=funcionario).order_by("-data_solicitacao")

    context = {
        "form_endereco": form_endereco,
        "form_bancario": form_bancario,
        "solicitacoes_endereco": solicitacoes_endereco,
        "solicitacoes_bancarias": solicitacoes_bancarias,
        "solicitacoes_abono": solicitacoes_abono,
        "funcionario_data": funcionario,
    }
    return render(request, "funcionarios/meu_perfil.html", context)


@login_required
def minha_jornada_view(request):
    funcionario = request.user.funcionario
    agora = timezone.now()

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

    def formatar_dias_semana(dias_str):
        dias_map = {'0': 'Seg', '1': 'Ter', '2': 'Qua', '3': 'Qui', '4': 'Sex', '5': 'Sáb', '6': 'Dom'}
        if not dias_str:
            return "N/A"
        dias_list = [dias_map.get(d.strip(), '') for d in dias_str.split(',')]
        return ", ".join(filter(None, dias_list))

    dias_de_trabalho = ""
    if escala_atual:
        dias_de_trabalho = formatar_dias_semana(escala_atual.escala.dias_semana)

    context = {
        "escala_atual": escala_atual,
        "dias_de_trabalho": dias_de_trabalho,
        "saldo_banco_horas": f"{saldo_horas}h {saldo_minutos_restantes}min",
        "saldo_banco_horas_negativo": saldo_total_minutos < 0,
        "funcionario_data": funcionario,
    }
    return render(request, "funcionarios/minha_jornada.html", context)


@login_required
@require_POST
def bate_ponto_view(request):
    funcionario = request.user.funcionario
    tipo_ponto = request.POST.get("tipo_ponto")
    agora = timezone.now()

    if not tipo_ponto:
        messages.error(request, "Você precisa selecionar um tipo de registro.")
        return redirect("funcionarios:home")

    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    if tipo_ponto == "ENTRADA":
        if RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="ENTRADA", timestamp__gte=inicio_do_dia
        ).exists():
            messages.error(request, "Você já registrou uma entrada hoje.")
            return redirect("funcionarios:home")

    if tipo_ponto == "SAIDA":
        if not RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="ENTRADA", timestamp__gte=inicio_do_dia
        ).exists():
            messages.error(
                request,
                "Você não pode registrar uma saída sem antes registrar uma entrada hoje.",
            )
            return redirect("funcionarios:home")
        if RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="SAIDA", timestamp__gte=inicio_do_dia
        ).exists():
            messages.error(request, "Você já registrou uma saída hoje.")
            return redirect("funcionarios:home")

    if funcionario.status != "ATIVO":
        messages.error(
            request,
            f"Seu status é '{funcionario.get_status_display()}', você não pode registrar o ponto.",
        )
        return redirect("funcionarios:home")

    if tipo_ponto == "ENTRADA":
        if funcionario.status_operacional != "OFFLINE":
            messages.error(
                request,
                f"Ação inválida. Seu status atual é '{funcionario.get_status_operacional_display()}'.",
            )
            return redirect("funcionarios:home")

        data_local = timezone.localtime(agora).date()
        solicitacao_aprovada = SolicitacaoHorario.objects.filter(
            funcionario=funcionario, status="APROVADO", data_hora_ponto__date=data_local
        ).exists()
        if not solicitacao_aprovada:
            escala_atual = (
                FuncionarioEscala.objects.filter(
                    funcionario=funcionario, data_inicio__lte=data_local
                )
                .filter(Q(data_fim__gte=data_local) | Q(data_fim__isnull=True))
                .first()
            )
            if not escala_atual:
                messages.error(
                    request, "Você não tem uma escala de trabalho definida. Contate o RH."
                )
                return redirect("funcionarios:home")

            dia_da_semana = data_local.weekday()
            if str(dia_da_semana) not in escala_atual.escala.dias_semana.split(","):
                messages.error(request, "Você não pode registrar o ponto em um dia de folga.")
                return redirect("funcionarios:home")

    if tipo_ponto == "SAIDA_PAUSA":
        if funcionario.status_operacional != "DISPONIVEL":
            messages.error(
                request, f"Você só pode iniciar uma pausa se estiver 'Disponível'."
            )
            return redirect("funcionarios:home")

        pausas_hoje_count = RegistroPonto.objects.filter(
            funcionario=funcionario, tipo="SAIDA_PAUSA", timestamp__gte=inicio_do_dia
        ).count()

        try:
            RegraDePausa.objects.get(cargo=funcionario.cargo, ordem=pausas_hoje_count + 1)
        except RegraDePausa.DoesNotExist:
            messages.error(
                request,
                "Você não tem mais pausas disponíveis ou elas não estão configuradas para seu cargo.",
            )
            return redirect("funcionarios:home")

    if tipo_ponto == "SAIDA_PAUSA_PESSOAL":
        if funcionario.status_operacional != "DISPONIVEL":
            messages.error(
                request, f"Você só pode iniciar uma pausa pessoal se estiver 'Disponível'."
            )
            return redirect("funcionarios:home")

    if tipo_ponto in ["VOLTA_PAUSA", "VOLTA_PAUSA_PESSOAL", "VOLTA_ALMOCO"]:
        if funcionario.status_operacional != "EM_PAUSA":
            messages.error(
                request, f"Você só pode voltar de uma pausa se estiver 'Em Pausa'."
            )
            return redirect("funcionarios:home")

    if tipo_ponto == "SAIDA":
        if funcionario.status_operacional not in ["DISPONIVEL", "EM_PAUSA"]:
            messages.error(
                request,
                f"Você não pode registrar a saída com o status '{funcionario.get_status_operacional_display()}'.",
            )
            return redirect("funcionarios:home")

    status_map = {
        "ENTRADA": "DISPONIVEL",
        "SAIDA_PAUSA": "EM_PAUSA",
        "VOLTA_PAUSA": "DISPONIVEL",
        "SAIDA_PAUSA_PESSOAL": "EM_PAUSA",
        "VOLTA_PAUSA_PESSOAL": "DISPONIVEL",
        "SAIDA_ALMOCO": "EM_PAUSA",
        "VOLTA_ALMOCO": "DISPONIVEL",
        "SAIDA": "OFFLINE",
    }
    funcionario.status_operacional = status_map.get(
        tipo_ponto, funcionario.status_operacional
    )
    funcionario.save()

    RegistroPonto.objects.create(funcionario=funcionario, tipo=tipo_ponto)
    messages.success(
        request, f"'{tipo_ponto.replace('_', ' ').title()}' registrada com sucesso!"
    )
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


@login_required
def solicitar_abono_view(request):
    funcionario = request.user.funcionario
    hoje = timezone.now().date()
    data_inicio_busca = max(hoje - timedelta(days=30), funcionario.data_contratacao)

    datas_com_registro = set(
        RegistroPonto.objects.filter(
            funcionario=funcionario, timestamp__date__gte=data_inicio_busca
        ).values_list("timestamp__date", flat=True)
    )
    datas_com_abono_pendente = set(
        SolicitacaoAbono.objects.filter(
            funcionario=funcionario,
            data_inicio__date__gte=data_inicio_busca,
            status="PENDENTE",
        ).values_list("data_inicio__date", flat=True)
    )

    faltas_nao_justificadas = []
    dias_a_verificar = (hoje - data_inicio_busca).days

    for i in range(dias_a_verificar + 1):
        data_atual = data_inicio_busca + timedelta(days=i)

        if (
            data_atual in datas_com_registro
            or data_atual in datas_com_abono_pendente
        ):
            continue

        escala_do_dia = (
            FuncionarioEscala.objects.filter(
                funcionario=funcionario, data_inicio__lte=data_atual
            )
            .filter(Q(data_fim__gte=data_atual) | Q(data_fim__isnull=True))
            .first()
        )

        if not escala_do_dia:
            continue

        dias_de_trabalho = [int(d) for d in escala_do_dia.escala.dias_semana.split(",")]
        if data_atual.weekday() in dias_de_trabalho:
            faltas_nao_justificadas.append(data_atual)

    if request.method == "POST":
        form = SolicitacaoAbonoForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            solicitacao = form.save(commit=False)
            solicitacao.funcionario = request.user.funcionario
            solicitacao.data_inicio = form.cleaned_data["data_inicio"]
            solicitacao.data_fim = form.cleaned_data["data_fim"]
            solicitacao.save()
            messages.success(
                request, "Sua solicitação de abono foi enviada para análise."
            )
            return redirect("funcionarios:home")
    else:
        form = SolicitacaoAbonoForm(request=request)
    context = {"form": form, "faltas": faltas_nao_justificadas}
    return render(request, "funcionarios/solicitar_abono.html", context)


from django.views.decorators.cache import never_cache

...

@never_cache
@login_required
def tabela_equipe_view(request):
    user = request.user
    is_analista_rh = user.groups.filter(name='Analista de RH').exists()

    if is_analista_rh:
        equipe = Funcionario.objects.filter(status='ATIVO')
    else:
        supervisor = get_object_or_404(Funcionario, user=user)
        equipe = supervisor.equipe.all()
        
    agora = timezone.now()
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    for membro in equipe:
        # Sincroniza o status do funcionário com base no seu último registro de ponto do dia.
        ultimo_registro = RegistroPonto.objects.filter(
            funcionario=membro,
            timestamp__gte=inicio_do_dia
        ).order_by('-timestamp').first()

        novo_status = 'OFFLINE'
        if ultimo_registro:
            if ultimo_registro.tipo == 'ENTRADA' or ultimo_registro.tipo.startswith('VOLTA_'):
                novo_status = 'DISPONIVEL'
            elif ultimo_registro.tipo in ['SAIDA_PAUSA', 'SAIDA_ALMOCO', 'SAIDA_PAUSA_PESSOAL']:
                novo_status = 'EM_PAUSA'
            # Se o tipo for 'SAIDA', o status permanece 'OFFLINE', que é o padrão.
        
        if membro.status_operacional != novo_status:
            membro.status_operacional = novo_status
            Funcionario.objects.filter(pk=membro.pk).update(status_operacional=novo_status)

        # Lógica para calcular tempo de pausa (permanece a mesma)
        membro.ultima_pausa = None
        membro.limite_pausa_segundos = 0
        if membro.status_operacional == "EM_PAUSA":
            ultima_pausa_registro = RegistroPonto.objects.filter(
                funcionario=membro, tipo__in=["SAIDA_PAUSA", "SAIDA_ALMOCO"]
            ).order_by("-timestamp").first()
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
        
        # Lógica da escala (permanece a mesma)
        membro.escala_atual = (
            FuncionarioEscala.objects.filter(
                funcionario=membro, data_inicio__lte=agora.date()
            )
            .filter(Q(data_fim__gte=agora.date()) | Q(data_fim__isnull=True))
            .first()
        )

    return render(request, "funcionarios/_tabela_equipe.html", {"equipe": equipe})


@login_required
def relatorio_folha_ponto(request):
    form = RelatorioFolhaPontoForm(user=request.user)
    relatorio_data = None

    def _calculate_paired_duration(registros, tipo_saida, tipo_volta):
        saidas = list(r for r in registros if r.tipo == tipo_saida)
        voltas = list(r for r in registros if r.tipo == tipo_volta)
        total_duration = timedelta()

        for s in saidas:
            corresponding_volta = next((v for v in voltas if v.timestamp > s.timestamp), None)
            if corresponding_volta:
                total_duration += corresponding_volta.timestamp - s.timestamp
                voltas.remove(corresponding_volta)
        
        return total_duration.total_seconds() / 60

    if request.method == "POST":
        form = RelatorioFolhaPontoForm(request.POST, user=request.user)
        if form.is_valid():
            data_inicio = form.cleaned_data["data_inicio"]
            data_fim = form.cleaned_data["data_fim"]
            funcionario_selecionado = form.cleaned_data["funcionario"]
            
            user = request.user
            is_analista_rh = user.groups.filter(name='Analista de RH').exists()
            is_supervisor = hasattr(user, 'funcionario') and user.funcionario.equipe.exists()
            
            pode_ver = False
            if is_analista_rh:
                pode_ver = True
            elif is_supervisor:
                if funcionario_selecionado == user.funcionario or user.funcionario.equipe.filter(id=funcionario_selecionado.id).exists():
                    pode_ver = True
            elif funcionario_selecionado == user.funcionario:
                pode_ver = True

            if not pode_ver:
                messages.error(request, "Você não tem permissão para visualizar o relatório deste funcionário.")
                return render(request, "funcionarios/relatorio_folha_ponto.html", {"form": form, "relatorio": None})

            funcionario = funcionario_selecionado
            current_timezone = timezone.get_current_timezone()
            start_range_aware = datetime.combine(data_inicio, time.min, tzinfo=current_timezone)
            end_range_aware = datetime.combine(data_fim, time.max, tzinfo=current_timezone)

            registros = (
                RegistroPonto.objects.filter(
                    funcionario=funcionario,
                    timestamp__range=(start_range_aware, end_range_aware),
                )
                .order_by("timestamp")
                .select_related("funcionario")
            )
            banco_horas = BancoDeHoras.objects.filter(
                funcionario=funcionario, data__range=(data_inicio, data_fim)
            )
            
            registros_por_dia = defaultdict(list)
            for registro in registros:
                dia_local = registro.timestamp.astimezone(current_timezone).date()
                registros_por_dia[dia_local].append(registro)

            banco_por_dia = {bh.data: bh for bh in banco_horas}
            relatorio_data = []
            dias_no_periodo = (data_fim - data_inicio).days + 1
            for dia_offset in range(dias_no_periodo):
                data_atual = data_inicio + timedelta(days=dia_offset)
                saldo_bh = banco_por_dia.get(data_atual)
                registros_do_dia = registros_por_dia.get(data_atual, [])
                
                jornada_bruta_minutos = _calculate_paired_duration(registros_do_dia, 'ENTRADA', 'SAIDA')
                minutos_pausa = _calculate_paired_duration(registros_do_dia, 'SAIDA_PAUSA', 'VOLTA_PAUSA')
                minutos_almoco = _calculate_paired_duration(registros_do_dia, 'SAIDA_ALMOCO', 'VOLTA_ALMOCO')
                minutos_pausa_pessoal = _calculate_paired_duration(registros_do_dia, 'SAIDA_PAUSA_PESSOAL', 'VOLTA_PAUSA_PESSOAL')
                total_horas_trabalhadas_minutos = jornada_bruta_minutos - minutos_pausa - minutos_almoco - minutos_pausa_pessoal

                status_dia = ""
                escala_info = (
                    FuncionarioEscala.objects.filter(
                        funcionario=funcionario, data_inicio__lte=data_atual
                    )
                    .filter(Q(data_fim__gte=data_atual) | Q(data_fim__isnull=True))
                    .first()
                )
                is_workday = False
                if escala_info:
                    dia_da_semana = data_atual.weekday()
                    if str(dia_da_semana) in escala_info.escala.dias_semana.split(","):
                        is_workday = True

                if is_workday and not registros_do_dia and not saldo_bh:
                    status_dia = "Falta Injustificada"
                elif is_workday and not registros_do_dia and saldo_bh and saldo_bh.descricao == 'Falta Injustificada':
                     status_dia = "Falta Injustificada"


                relatorio_data.append(
                    {
                        "data": data_atual,
                        "registros": registros_do_dia,
                        "saldo_bh": saldo_bh,
                        "status": status_dia,
                        "total_horas_trabalhadas": total_horas_trabalhadas_minutos,
                    }
                )
    context = {"form": form, "relatorio": relatorio_data}
    return render(request, "funcionarios/relatorio_folha_ponto.html", context)


@login_required
def relatorio_equipe_view(request):
    if not request.user.is_superuser and not request.user.funcionario.equipe.exists():
        messages.error(request, "Você não tem permissão para acessar esta página.")
        return redirect("funcionarios:home")
    form = RelatorioEquipeForm()
    relatorio_data = None
    totais = None
    if request.method == "POST":
        form = RelatorioEquipeForm(request.POST)
        if form.is_valid():
            data_inicio = form.cleaned_data["data_inicio"]
            data_fim = form.cleaned_data["data_fim"]
            supervisor = request.user.funcionario
            equipe = supervisor.equipe.all() if not request.user.is_superuser else Funcionario.objects.all()
            relatorio_data = []
            total_geral_extras = 0
            total_geral_devidas = 0
            total_geral_faltas = 0
            for funcionario in equipe:
                banco_horas = BancoDeHoras.objects.filter(
                    funcionario=funcionario, data__range=(data_inicio, data_fim)
                )
                horas_extras_minutos = banco_horas.filter(minutos__gt=0).aggregate(total=Sum('minutos'))['total'] or 0
                horas_devidas_minutos = banco_horas.filter(minutos__lt=0).aggregate(total=Sum('minutos'))['total'] or 0
                faltas = 0
                dias_no_periodo = (data_fim - data_inicio).days + 1
                for dia_offset in range(dias_no_periodo):
                    data_atual = data_inicio + timedelta(days=dia_offset)
                    tem_registro = RegistroPonto.objects.filter(funcionario=funcionario, timestamp__date=data_atual).exists()
                    tem_abono = SolicitacaoAbono.objects.filter(
                        funcionario=funcionario,
                        data_inicio__date=data_atual,
                        status='APROVADO'
                    ).exists()
                    if tem_registro or tem_abono:
                        continue
                    escala_info = FuncionarioEscala.objects.filter(
                        funcionario=funcionario, data_inicio__lte=data_atual
                    ).filter(Q(data_fim__gte=data_atual) | Q(data_fim__isnull=True)).first()
                    if escala_info:
                        dia_da_semana = data_atual.weekday()
                        if str(dia_da_semana) in escala_info.escala.dias_semana.split(","):
                            faltas += 1
                relatorio_data.append({
                    'funcionario': funcionario,
                    'horas_extras_minutos': horas_extras_minutos,
                    'horas_devidas_minutos': abs(horas_devidas_minutos),
                    'faltas': faltas,
                })
                total_geral_extras += horas_extras_minutos
                total_geral_devidas += abs(horas_devidas_minutos)
                total_geral_faltas += faltas
            totais = {
                'total_geral_extras_minutos': total_geral_extras,
                'total_geral_devidas_minutos': total_geral_devidas,
                'total_geral_faltas': total_geral_faltas,
            }
    context = {"form": form, "relatorio": relatorio_data, "totais": totais}
    return render(request, "funcionarios/relatorio_equipe.html", context)


def logout_view(request):
    logout(request)
    return redirect("funcionarios:login")


@login_required
def aprovar_solicitacao_horario(request, pk):
    solicitacao = get_object_or_404(SolicitacaoHorario, pk=pk)
    user = request.user
    
    is_analista_rh = user.groups.filter(name='Analista de RH').exists()
    is_supervisor_direto = hasattr(user, 'funcionario') and solicitacao.funcionario.supervisor == user.funcionario

    if is_analista_rh or is_supervisor_direto:
        solicitacao.status = "APROVADO"
        solicitacao.analisado_por = user.funcionario
        solicitacao.data_analise = timezone.now()
        solicitacao.save()
        messages.success(request, "A solicitação foi aprovada com sucesso.")
    else:
        messages.error(request, "Você não tem permissão para aprovar esta solicitação.")

    return redirect("funcionarios:supervisor_dashboard")


@login_required
def recusar_solicitacao_horario(request, pk):
    solicitacao = get_object_or_404(SolicitacaoHorario, pk=pk)
    user = request.user

    is_analista_rh = user.groups.filter(name='Analista de RH').exists()
    is_supervisor_direto = hasattr(user, 'funcionario') and solicitacao.funcionario.supervisor == user.funcionario

    if is_analista_rh or is_supervisor_direto:
        solicitacao.status = "RECUSADO"
        solicitacao.analisado_por = user.funcionario
        solicitacao.data_analise = timezone.now()
        solicitacao.save()
        messages.success(request, "A solicitação foi recusada.")
    else:
        messages.error(request, "Você não tem permissão para recusar esta solicitação.")

    return redirect("funcionarios:supervisor_dashboard")


@login_required
def aprovar_solicitacao_abono(request, pk):
    solicitacao = get_object_or_404(SolicitacaoAbono, pk=pk)
    user = request.user

    is_analista_rh = user.groups.filter(name='Analista de RH').exists()
    is_supervisor_direto = hasattr(user, 'funcionario') and solicitacao.funcionario.supervisor == user.funcionario

    if is_analista_rh or is_supervisor_direto:
        solicitacao.status = "APROVADO"
        solicitacao.analisado_por = user.funcionario
        solicitacao.data_analise = timezone.now()
        solicitacao.save()

        messages.success(request, "A solicitação de abono foi aprovada.")
    else:
        messages.error(request, "Você não tem permissão para aprovar esta solicitação.")

    return redirect("funcionarios:supervisor_dashboard")


@login_required
def recusar_solicitacao_abono(request, pk):
    solicitacao = get_object_or_404(SolicitacaoAbono, pk=pk)
    user = request.user

    is_analista_rh = user.groups.filter(name='Analista de RH').exists()
    is_supervisor_direto = hasattr(user, 'funcionario') and solicitacao.funcionario.supervisor == user.funcionario

    if is_analista_rh or is_supervisor_direto:
        solicitacao.status = "RECUSADO"
        solicitacao.analisado_por = user.funcionario
        solicitacao.data_analise = timezone.now()
        solicitacao.save()
        messages.success(request, "A solicitação de abono foi recusada.")
    else:
        messages.error(request, "Você não tem permissão para recusar esta solicitação.")

    return redirect("funcionarios:supervisor_dashboard")
