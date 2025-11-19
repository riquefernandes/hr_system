# funcionarios/forms.py
from django import forms
from .models import (
    Funcionario,
    FuncionarioEscala,
    SolicitacaoAbono,
    SolicitacaoAlteracaoEndereco,
    SolicitacaoAlteracaoBancaria,
    SolicitacaoHorario,
)
from django.db.models import Q
from datetime import datetime, time


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class SolicitacaoAbonoForm(forms.ModelForm):
    data_falta = forms.DateField(
        label="Data da Falta", required=False, widget=DateInput
    )
    data_inicio_horas = forms.DateTimeField(
        label="Início do Período", required=False, widget=DateTimeInput
    )
    data_fim_horas = forms.DateTimeField(
        label="Fim do Período", required=False, widget=DateTimeInput
    )

    class Meta:
        model = SolicitacaoAbono
        fields = ["tipo_abono", "motivo", "documento"]
        widgets = {
            "motivo": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "tipo_abono": "Tipo de Abono",
            "motivo": "Motivo da Solicitação",
            "documento": "Anexar Documento (Opcional)",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        tipo_abono = cleaned_data.get("tipo_abono")
        data_falta = cleaned_data.get("data_falta")
        data_inicio_horas = cleaned_data.get("data_inicio_horas")
        data_fim_horas = cleaned_data.get("data_fim_horas")

        data_para_validar = None

        if tipo_abono == "FALTA":
            if not data_falta:
                self.add_error("data_falta", "Este campo é obrigatório para abono de falta.")
            else:
                # Converte para datetime para salvar no modelo
                cleaned_data["data_inicio"] = datetime.combine(data_falta, time.min)
                cleaned_data["data_fim"] = datetime.combine(data_falta, time.max)
                data_para_validar = data_falta

        elif tipo_abono == "ATRASO":
            if not data_inicio_horas or not data_fim_horas:
                self.add_error(
                    "data_inicio_horas",
                    "Os campos de início e fim do período são obrigatórios.",
                )
            else:
                if data_fim_horas <= data_inicio_horas:
                    self.add_error(
                        "data_fim_horas", "A data/hora final deve ser após a inicial."
                    )
                cleaned_data["data_inicio"] = data_inicio_horas
                cleaned_data["data_fim"] = data_fim_horas
                data_para_validar = data_inicio_horas.date()

        # Validação do dia de trabalho
        if data_para_validar and self.request:
            funcionario = self.request.user.funcionario
            escala_info = (
                FuncionarioEscala.objects.filter(
                    funcionario=funcionario, data_inicio__lte=data_para_validar
                )
                .filter(
                    Q(data_fim__gte=data_para_validar) | Q(data_fim__isnull=True)
                )
                .first()
            )

            is_workday = False
            if escala_info:
                dia_da_semana = data_para_validar.weekday()
                if str(dia_da_semana) in escala_info.escala.dias_semana.split(","):
                    is_workday = True

            if not is_workday:
                self.add_error(
                    None,  # Erro não associado a um campo específico
                    f"A data {data_para_validar.strftime('%d/%m/%Y')} não é um dia de trabalho na sua escala.",
                )

        return cleaned_data


class RelatorioFolhaPontoForm(forms.Form):
    data_inicio = forms.DateField(label="Data de Início", widget=DateInput)
    data_fim = forms.DateField(label="Data de Fim", widget=DateInput)
    funcionario = forms.ModelChoiceField(
        queryset=Funcionario.objects.none(),  # Queryset será definido na view
        label="Funcionário",
        required=False,
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        if not user or not hasattr(user, 'funcionario'):
            # Se não houver usuário ou funcionário associado, não mostra ninguém
            self.fields["funcionario"].queryset = Funcionario.objects.none()
            return

        is_analista_rh = user.groups.filter(name='Analista de RH').exists()
        is_supervisor = user.funcionario.equipe.exists()

        if is_analista_rh:
            # Analista de RH pode ver todos os funcionários ativos
            self.fields["funcionario"].queryset = Funcionario.objects.filter(status='ATIVO')
            self.fields["funcionario"].label = "Selecionar Funcionário"
        
        elif is_supervisor:
            # Supervisor pode ver a si mesmo e sua equipe
            self.fields["funcionario"].queryset = (
                user.funcionario.equipe.all() | Funcionario.objects.filter(id=user.funcionario.id)
            ).distinct()
            self.fields["funcionario"].label = "Selecionar Membro da Equipe"

        else:
            # Funcionário comum só pode ver o próprio relatório
            self_qs = Funcionario.objects.filter(id=user.funcionario.id)
            self.fields["funcionario"].queryset = self_qs
            self.fields["funcionario"].initial = user.funcionario
            self.fields["funcionario"].widget = forms.HiddenInput()



class RelatorioEquipeForm(forms.Form):
    data_inicio = forms.DateField(label="Data de Início", widget=DateInput)
    data_fim = forms.DateField(label="Data de Fim", widget=DateInput)


# Este é o nosso novo formulário para endereço
class SolicitacaoAlteracaoEnderecoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAlteracaoEndereco
        fields = ["cep", "rua", "numero", "bairro", "cidade", "estado", "complemento"]
        labels = {
            "cep": "CEP",
            "rua": "Rua / Logradouro",
            "numero": "Número",
            "bairro": "Bairro",
            "cidade": "Cidade",
            "estado": "Estado (UF)",
            "complemento": "Complemento (Opcional)",
        }


# O formulário bancário continua o mesmo
class SolicitacaoAlteracaoBancariaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAlteracaoBancaria
        fields = ["banco", "agencia", "conta"]
        labels = {
            "banco": "Novo Banco",
            "agencia": "Nova Agência",
            "conta": "Nova Conta",
        }


class SolicitacaoHorarioForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoHorario
        fields = ["motivo"]  # Apenas o motivo é preenchido pelo usuário
        widgets = {
            "motivo": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "motivo": "Por qual motivo você precisa registrar o ponto fora do seu horário?",
        }
