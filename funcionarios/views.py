# funcionarios/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .forms import SolicitacaoAlteracaoEnderecoForm, SolicitacaoAlteracaoBancariaForm
from .models import SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoBancaria

# Nossos formulários e modelos atualizados
from .forms import SolicitacaoAlteracaoEnderecoForm, SolicitacaoAlteracaoBancariaForm
from .models import SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoBancaria

def login_view(request):
    if request.method == 'POST':
        matricula = request.POST.get('username')
        senha = request.POST.get('password')
        user = authenticate(request, username=matricula, password=senha)
        if user is not None:
            login(request, user)
            return redirect('funcionarios:home')
        else:
            return render(request, 'funcionarios/login.html')
    else:
        return render(request, 'funcionarios/login.html')

@login_required
def home_view(request):
    funcionario = request.user.funcionario
    
    # Instancia os dois formulários
    form_endereco = SolicitacaoAlteracaoEnderecoForm()
    form_bancario = SolicitacaoAlteracaoBancariaForm()

    if request.method == 'POST':
        # Verifica qual formulário foi enviado pelo nome do botão
        if 'submit_endereco' in request.POST:
            form_endereco = SolicitacaoAlteracaoEnderecoForm(request.POST)
            if form_endereco.is_valid():
                solicitacao = form_endereco.save(commit=False)
                solicitacao.funcionario = funcionario
                solicitacao.save()
                return redirect('funcionarios:home')
        
        elif 'submit_bancario' in request.POST:
            form_bancario = SolicitacaoAlteracaoBancariaForm(request.POST)
            if form_bancario.is_valid():
                solicitacao = form_bancario.save(commit=False)
                solicitacao.funcionario = funcionario
                solicitacao.save()
                return redirect('funcionarios:home')

    # Busca o histórico de ambas as solicitações
    solicitacoes_endereco = SolicitacaoAlteracaoEndereco.objects.filter(funcionario=funcionario).order_by('-data_solicitacao')
    solicitacoes_bancarias = SolicitacaoAlteracaoBancaria.objects.filter(funcionario=funcionario).order_by('-data_solicitacao')

    context = {
        'funcionario_data': funcionario,
        'form_endereco': form_endereco,
        'form_bancario': form_bancario,
        'solicitacoes_endereco': solicitacoes_endereco,
        'solicitacoes_bancarias': solicitacoes_bancarias,
    }
    return render(request, 'funcionarios/home.html', context)

def logout_view(request):
    logout(request)
    return redirect('funcionarios:login')