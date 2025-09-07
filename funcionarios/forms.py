# funcionarios/forms.py
from django import forms
# Atualizamos a importação para os modelos corretos
from .models import SolicitacaoAlteracaoEndereco, SolicitacaoAlteracaoBancaria

# Este é o nosso novo formulário para endereço
class SolicitacaoAlteracaoEnderecoForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAlteracaoEndereco
        fields = ['cep', 'rua', 'numero', 'bairro', 'cidade', 'estado', 'complemento']
        labels = {
            'cep': 'CEP',
            'rua': 'Rua / Logradouro',
            'numero': 'Número',
            'bairro': 'Bairro',
            'cidade': 'Cidade',
            'estado': 'Estado (UF)',
            'complemento': 'Complemento (Opcional)',
        }

# O formulário bancário continua o mesmo
class SolicitacaoAlteracaoBancariaForm(forms.ModelForm):
    class Meta:
        model = SolicitacaoAlteracaoBancaria
        fields = ['banco', 'agencia', 'conta']
        labels = {
            'banco': 'Novo Banco',
            'agencia': 'Nova Agência',
            'conta': 'Nova Conta',
        }