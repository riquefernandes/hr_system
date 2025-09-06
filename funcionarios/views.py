# funcionarios/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

# CORREÇÃO ESTÁ NESTA LINHA DE IMPORT:
from .forms import SolicitacaoAlteracaoSimplesForm, SolicitacaoAlteracaoBancariaForm
from .models import SolicitacaoAlteracaoSimples, SolicitacaoAlteracaoBancaria

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
    
    form_simples = SolicitacaoAlteracaoSimplesForm()
    form_bancario = SolicitacaoAlteracaoBancariaForm()

    if request.method == 'POST':
        if 'submit_simples' in request.POST:
            form_simples = SolicitacaoAlteracaoSimplesForm(request.POST)
            if form_simples.is_valid():
                solicitacao = form_simples.save(commit=False)
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

    solicitacoes_simples = SolicitacaoAlteracaoSimples.objects.filter(funcionario=funcionario).order_by('-data_solicitacao')
    solicitacoes_bancarias = SolicitacaoAlteracaoBancaria.objects.filter(funcionario=funcionario).order_by('-data_solicitacao')

    context = {
        'funcionario_data': funcionario,
        'form_simples': form_simples,
        'form_bancario': form_bancario,
        'solicitacoes_simples': solicitacoes_simples,
        'solicitacoes_bancarias': solicitacoes_bancarias,
    }
    return render(request, 'funcionarios/home.html', context)

def logout_view(request):
    logout(request)
    return redirect('funcionarios:login')