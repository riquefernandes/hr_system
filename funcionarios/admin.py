# funcionarios/admin.py (VERSÃO FINAL E CORRIGIDA)
from django.contrib import admin
from .models import (
    Cargo, CentroDeCusto, Banco, Funcionario, 
    SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoBancaria
)
from django.utils import timezone

# --- CLASSE DE ADMIN PARA FUNCIONARIO ---
class FuncionarioAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('nome_completo', 'data_nascimento', 'sexo')
        }),
        ('Documentos', {
            'fields': ('cpf', 'rg')
        }),
        ('Endereço', {
            'fields': ('cep', 'rua', 'numero', 'bairro', 'cidade', 'estado', 'complemento')
        }),
        ('Dados de Trabalho', {
            'fields': ('cargo', 'centro_de_custo')
        }),
        ('Dados Bancários', {
            'fields': ('banco', 'agencia', 'conta')
        }),
    )
    list_display = ('nome_completo', 'cpf', 'cargo')
    # --- CORREÇÃO NESTA LINHA ---
    list_filter = ('cargo', 'centro_de_custo', 'banco')
    search_fields = ('nome_completo', 'cpf')
class Media:
        js = ('funcionarios/js/cep_lookup.js',)
# --- Ações Customizadas ---
@admin.action(description='Aprovar solicitações de endereço selecionadas')
def aprovar_solicitacoes_endereco(modeladmin, request, queryset):
    for solicitacao in queryset:
        f = solicitacao.funcionario
        f.cep, f.rua, f.numero, f.bairro, f.cidade, f.estado, f.complemento = \
        solicitacao.cep, solicitacao.rua, solicitacao.numero, solicitacao.bairro, solicitacao.cidade, solicitacao.estado, solicitacao.complemento
        f.save()
        solicitacao.status = 'A'; solicitacao.data_aprovacao = timezone.now(); solicitacao.save()

@admin.action(description='Aprovar solicitações bancárias selecionadas')
def aprovar_solicitacoes_bancarias(modeladmin, request, queryset):
    for solicitacao in queryset:
        funcionario = solicitacao.funcionario
        funcionario.banco = solicitacao.banco
        funcionario.agencia = solicitacao.agencia
        funcionario.conta = solicitacao.conta
        funcionario.save()
        solicitacao.status = 'A'
        solicitacao.data_aprovacao = timezone.now()
        solicitacao.save()

# --- Classes de Admin Customizadas para Solicitações ---
class SolicitacaoAlteracaoEnderecoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'cep', 'cidade', 'status')
    actions = [aprovar_solicitacoes_endereco]

class SolicitacaoAlteracaoBancariaAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'banco', 'agencia', 'conta', 'status')
    actions = [aprovar_solicitacoes_bancarias]

# --- Registros no Admin ---
admin.site.register(Cargo)
admin.site.register(CentroDeCusto)
admin.site.register(Banco)
admin.site.register(Funcionario, FuncionarioAdmin)
admin.site.register(SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoEnderecoAdmin)
admin.site.register(SolicitacaoAlteracaoBancaria, SolicitacaoAlteracaoBancariaAdmin)