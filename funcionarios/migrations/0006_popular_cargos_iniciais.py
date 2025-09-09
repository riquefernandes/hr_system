# (dentro do novo arquivo de migração)
from django.db import migrations

# Nossa lista de cargos padrão
CARGOS_INICIAIS = [
    "Operador de Atendimento",
    "Supervisor de Equipe",
    "Analista de Qualidade",
    "Analista de RH",
    "Gerente de Operações",
    "Diretor",
    "Analista de Planejamento (WFM)",
    "Suporte de TI",
]


def popular_cargos(apps, schema_editor):
    """
    Pega cada nome da lista e cria um objeto Cargo no banco de dados.
    """
    Cargo = apps.get_model("funcionarios", "Cargo")
    for nome_cargo in CARGOS_INICIAIS:
        # get_or_create evita criar cargos duplicados se a migração for rodada mais de uma vez
        Cargo.objects.get_or_create(nome=nome_cargo)


class Migration(migrations.Migration):

    # Esta migração precisa rodar DEPOIS da migração que criou a tabela Cargo
    dependencies = [
        (
            "funcionarios",
            "0001_initial",
        ),  # ATENÇÃO: Verifique se o nome do seu arquivo de migração inicial é este
    ]

    operations = [
        migrations.RunPython(popular_cargos),
    ]
