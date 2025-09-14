# funcionarios/forms.py
from django import forms
from .models import (
    Funcionario,
    SolicitacaoAbono,
    SolicitacaoAlteracaoEndereco,
    SolicitacaoAlteracaoBancaria,
    SolicitacaoHorario,
)


class DateInput(forms.DateInput):
    input_type = "date"


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


class SolicitacaoAbonoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAbono
        fields = ["tipo_abono", "data_inicio", "data_fim", "motivo", "documento"]
        widgets = {
            "data_inicio": DateTimeInput(),
            "data_fim": DateTimeInput(),
            "motivo": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "tipo_abono": "Tipo de Abono",
            "data_inicio": "Início do Período para Abono",
            "data_fim": "Fim do Período para Abono",
            "motivo": "Motivo da Solicitação",
            "documento": "Anexar Documento (Opcional)",
        }


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

        if user and user.funcionario.supervisor:
            # Se o usuário for um supervisor, ele não pode selecionar funcionários
            self.fields["funcionario"].queryset = Funcionario.objects.filter(
                id=user.funcionario.id
            )
            self.fields["funcionario"].initial = user.funcionario
            self.fields["funcionario"].disabled = True
        elif user and hasattr(user, "funcionario") and user.funcionario.equipe.exists():
            # Se for um supervisor, pode escolher entre sua equipe
            self.fields["funcionario"].queryset = user.funcionario.equipe.all()
        elif user and hasattr(user, "funcionario"):
            # Funcionário comum só pode ver o próprio relatório
            self.fields["funcionario"].queryset = Funcionario.objects.filter(
                id=user.funcionario.id
            )
            self.fields["funcionario"].initial = user.funcionario
            self.fields["funcionario"].widget = forms.HiddenInput()


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
