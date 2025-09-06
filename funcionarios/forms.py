# funcionarios/forms.py
from django import forms
from .models import SolicitacaoAlteracaoSimples, SolicitacaoAlteracaoBancaria

class SolicitacaoAlteracaoSimplesForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAlteracaoSimples
        fields = ['campo', 'novo_valor']
        labels = {
            'campo': 'O que você quer alterar?',
            'novo_valor': 'Qual o novo valor?',
        }

class SolicitacaoAlteracaoBancariaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAlteracaoBancaria
        fields = ['banco', 'agencia', 'conta']
        labels = {
            'banco': 'Novo Banco',
            'agencia': 'Nova Agência',
            'conta': 'Nova Conta',
        }