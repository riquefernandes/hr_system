# funcionarios/admin.py (VERSÃO FINAL E CORRIGIDA)
from django.contrib import admin
from .models import (
    Cargo,
    CentroDeCusto,
    Banco,
    Funcionario,
    SolicitacaoAlteracaoEndereco,
    SolicitacaoAlteracaoBancaria,
    RegraDePausa,
    # Novos modelos para Escala e Banco de Horas
    Escala,
    FuncionarioEscala,
    BancoDeHoras,
    SolicitacaoHorario,
    Feriado,
)
from django.utils import timezone


# --- INLINE PARA ESCALAS DO FUNCIONÁRIO ---
class FuncionarioEscalaInline(admin.TabularInline):
    model = FuncionarioEscala
    extra = 1


# --- CLASSE DE ADMIN PARA FUNCIONARIO ---
class FuncionarioAdmin(admin.ModelAdmin):
    readonly_fields = ("email_usuario", "matricula_usuario")
    fieldsets = (
        (
            "Informações de Login",
            {"fields": ("matricula_usuario", "email_usuario", "status")},
        ),
        (
            "Informações Pessoais",
            {
                "fields": (
                    "nome_completo",
                    "data_nascimento",
                    "sexo",
                    "email_pessoal",
                    "telefone_celular",
                    "escolaridade",
                )
            },
        ),
        (
            "Contato de Emergência",
            {"fields": ("contato_emergencia_nome", "contato_emergencia_telefone")},
        ),
        ("Datas de Contrato", {"fields": ("data_contratacao", "data_demissao")}),
        ("Documentos", {"fields": ("cpf", "rg")}),
        (
            "Endereço",
            {
                "fields": (
                    "cep",
                    "rua",
                    "numero",
                    "bairro",
                    "cidade",
                    "estado",
                    "complemento",
                )
            },
        ),
        ("Dados de Trabalho", {"fields": ("cargo", "centro_de_custo", "supervisor")}),
        ("Dados Bancários", {"fields": ("banco", "agencia", "conta")}),
    )
    list_display = ("nome_completo", "matricula_usuario", "cpf", "cargo", "status")
    list_filter = ("status", "cargo", "centro_de_custo", "banco")
    search_fields = ("nome_completo", "cpf", "user__username")
    inlines = [FuncionarioEscalaInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "supervisor":
            kwargs["queryset"] = Funcionario.objects.filter(
                cargo__nome="Supervisor de Equipe"
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Email (do login)")
    def email_usuario(self, obj):
        if obj.user:
            return obj.user.email
        return "Será gerado ao salvar"

    @admin.display(description="Matrícula")
    def matricula_usuario(self, obj):
        if obj.user:
            return obj.user.username
        return "Será gerada ao salvar"


# --- INLINE PARA REGRAS DE PAUSA ---
class RegraDePausaInline(admin.TabularInline):
    model = RegraDePausa
    extra = 1  # Mostra 1 campo extra em branco para adicionar novas regras


# --- CLASSE DE ADMIN PARA CARGO ---
class CargoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cbo")
    search_fields = ("nome", "cbo")
    inlines = [RegraDePausaInline]  # Adiciona as regras de pausa na página do cargo


# --- Ações Customizadas ---
@admin.action(description="Aprovar solicitações de endereço selecionadas")
def aprovar_solicitacoes_endereco(modeladmin, request, queryset):
    for solicitacao in queryset:
        f = solicitacao.funcionario
        (f.cep, f.rua, f.numero, f.bairro, f.cidade, f.estado, f.complemento) = (
            solicitacao.cep,
            solicitacao.rua,
            solicitacao.numero,
            solicitacao.bairro,
            solicitacao.cidade,
            solicitacao.estado,
            solicitacao.complemento,
        )
        f.save()
        solicitacao.status = "A"
        solicitacao.data_aprovacao = timezone.now()
        solicitacao.save()


@admin.action(description="Aprovar solicitações bancárias selecionadas")
def aprovar_solicitacoes_bancarias(modeladmin, request, queryset):
    for solicitacao in queryset:
        f = solicitacao.funcionario
        f.banco, f.agencia, f.conta = (
            solicitacao.banco,
            solicitacao.agencia,
            solicitacao.conta,
        )
        f.save()
        solicitacao.status = "A"
        solicitacao.data_aprovacao = timezone.now()
        solicitacao.save()


# --- Classes de Admin Customizadas para Solicitações ---
class SolicitacaoAlteracaoEnderecoAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "cep", "cidade", "status")
    actions = [aprovar_solicitacoes_endereco]


class SolicitacaoAlteracaoBancariaAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "banco", "agencia", "conta", "status")
    actions = [aprovar_solicitacoes_bancarias]


# --- Registros no Admin ---
admin.site.register(Cargo, CargoAdmin)  # Atualizado para usar a classe customizada
admin.site.register(CentroDeCusto)
admin.site.register(Banco)
admin.site.register(Funcionario, FuncionarioAdmin)
admin.site.register(SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoEnderecoAdmin)
admin.site.register(SolicitacaoAlteracaoBancaria, SolicitacaoAlteracaoBancariaAdmin)
admin.site.register(RegraDePausa)  # Opcional, para gerenciar todas as regras de uma vez


# --- Classes de Admin para Escala e Banco de Horas ---
@admin.register(Escala)
class EscalaAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "horario_entrada",
        "horario_saida",
        "dias_semana",
        "duracao_almoco_minutos",
        "prioritaria",  # Adicionado aqui
    )
    list_filter = ("prioritaria",)  # E aqui
    search_fields = ("nome",)


@admin.register(BancoDeHoras)
class BancoDeHorasAdmin(admin.ModelAdmin):
    list_display = ("funcionario", "data", "minutos", "descricao", "processado_em")
    list_filter = ("funcionario", "data")
    search_fields = ("funcionario__nome_completo", "descricao")

    # Torna o admin de Banco de Horas somente leitura, pois será populado pelo sistema
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SolicitacaoHorario)
class SolicitacaoHorarioAdmin(admin.ModelAdmin):
    list_display = (
        "funcionario",
        "data_hora_ponto",
        "status",
        "analisado_por",
        "data_analise",
    )
    list_filter = ("status",)
    search_fields = ("funcionario__nome_completo",)
    readonly_fields = (
        "funcionario",
        "data_hora_ponto",
        "motivo",
        "analisado_por",
        "data_analise",
        "data_solicitacao",
    )


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    list_display = ("nome", "data", "recorrente")
    list_filter = ("recorrente",)
    search_fields = ("nome",)

