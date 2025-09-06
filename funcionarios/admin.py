# funcionarios/admin.py
from django.contrib import admin
from .models import (
    Cargo, CentroDeCusto, Banco, Funcionario, 
    SolicitacaoAlteracaoSimples, SolicitacaoAlteracaoBancaria
)
from django.utils import timezone

# --- Ações Customizadas ---

@admin.action(description='Aprovar solicitações de endereço selecionadas')
def aprovar_solicitacoes_simples(modeladmin, request, queryset):
    """
    Ação para aprovar solicitações simples, como mudança de endereço.
    """
    for solicitacao in queryset:
        funcionario = solicitacao.funcionario
        campo_para_alterar = solicitacao.campo
        novo_valor = solicitacao.novo_valor

        # Altera o dado no cadastro do funcionário dinamicamente
        setattr(funcionario, campo_para_alterar, novo_valor)
        funcionario.save()

        # Atualiza o status da solicitação
        solicitacao.status = 'A'  # 'A' de Aprovado
        solicitacao.data_aprovacao = timezone.now()
        solicitacao.save()

@admin.action(description='Aprovar solicitações bancárias selecionadas')
def aprovar_solicitacoes_bancarias(modeladmin, request, queryset):
    """
    Ação específica para aprovar as solicitações de dados bancários.
    """
    for solicitacao in queryset:
        funcionario = solicitacao.funcionario
        
        # Copia os novos dados bancários da solicitação para o funcionário
        funcionario.banco = solicitacao.banco
        funcionario.agencia = solicitacao.agencia
        funcionario.conta = solicitacao.conta
        funcionario.save()

        # Atualiza o status da solicitação
        solicitacao.status = 'A'
        solicitacao.data_aprovacao = timezone.now()
        solicitacao.save()

# --- Classes de Admin Customizadas ---

class SolicitacaoAlteracaoSimplesAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'campo', 'novo_valor', 'status', 'data_solicitacao')
    list_filter = ('status', 'campo')
    actions = [aprovar_solicitacoes_simples]

class SolicitacaoAlteracaoBancariaAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'banco', 'agencia', 'conta', 'status', 'data_solicitacao')
    list_filter = ('status', 'banco')
    actions = [aprovar_solicitacoes_bancarias]

# --- Registros no Admin ---

admin.site.register(Cargo)
admin.site.register(CentroDeCusto)
admin.site.register(Banco)
admin.site.register(Funcionario)
admin.site.register(SolicitacaoAlteracaoSimples, SolicitacaoAlteracaoSimplesAdmin)
admin.site.register(SolicitacaoAlteracaoBancaria, SolicitacaoAlteracaoBancariaAdmin)