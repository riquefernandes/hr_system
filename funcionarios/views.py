# funcionarios/views.py (VERSÃO FINAL COM TROCA DE SENHA)
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

# Importa a view de troca de senha original do Django
from django.contrib.auth.views import PasswordChangeView

from .forms import SolicitacaoAlteracaoEnderecoForm, SolicitacaoAlteracaoBancariaForm
from .models import SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoBancaria


def login_view(request):
    # ... (esta função não muda)
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


# --- NOSSA NOVA VIEW CUSTOMIZADA ---
class CustomPasswordChangeView(PasswordChangeView):
    # Sobrescreve o método que é chamado quando o formulário é válido
    def form_valid(self, form):
        # Pega o funcionário logado
        funcionario = self.request.user.funcionario
        # Abaixa a bandeira
        funcionario.deve_alterar_senha = False
        funcionario.save()
        # Continua o processo normal da view original
        return super().form_valid(form)


def supervisor_dashboard_view(request):
    # Primeiro, verificamos se o usuário tem a permissão para ver a página
    # Ou se é um superusuário (que pode tudo)
    if (
        not request.user.has_perm("funcionarios.view_funcionario")
        and not request.user.is_superuser
    ):
        # Redireciona para a home normal se não tiver permissão
        return redirect("funcionarios:home")

    # Pega o objeto do supervisor logado
    supervisor_logado = request.user.funcionario

    # Usa o 'related_name' que criamos para pegar a equipe dele!
    equipe_do_supervisor = supervisor_logado.equipe.all()

    context = {"supervisor": supervisor_logado, "equipe": equipe_do_supervisor}
    return render(request, "funcionarios/supervisor_dashboard.html", context)


@login_required
def home_view(request):
    # ... (esta função não muda)
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
    }
    return render(request, "funcionarios/home.html", context)


def logout_view(request):
    # ... (esta função não muda)
    logout(request)
    return redirect("funcionarios:login")
