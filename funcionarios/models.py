# funcionarios/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from localflavor.br.models import BRCPFField


class Escala(models.Model):
    """Define um padrão de horário de trabalho e dias da semana."""

    nome = models.CharField(
        max_length=100, unique=True, help_text="Ex: Seg-Sáb 08:00-14:20"
    )
    dias_semana = models.CharField(
        max_length=15,
        help_text="Dias da semana separados por vírgula (0=Seg, 1=Ter, ..., 6=Dom).",
    )
    horario_entrada = models.TimeField()
    horario_saida = models.TimeField()
    duracao_almoco_minutos = models.PositiveIntegerField(
        default=60, help_text="Duração do intervalo de almoço padrão em minutos."
    )

    class Meta:
        verbose_name = "Escala de Trabalho"
        verbose_name_plural = "Escalas de Trabalho"

    def __str__(self):
        return self.nome


class Cargo(models.Model):
    nome = models.CharField(max_length=255)
    cbo = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        help_text="Digite o código CBO (ex: 4223-10) e saia do campo.",
    )
    escala_padrao = models.ForeignKey(
        Escala,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="A escala padrão para novos funcionários neste cargo.",
    )

    def __str__(self):
        return self.nome


class RegraDePausa(models.Model):
    cargo = models.ForeignKey(
        Cargo, on_delete=models.CASCADE, related_name="regras_de_pausa"
    )
    nome = models.CharField(max_length=100, help_text="Ex: Pausa Café 1")
    ordem = models.PositiveIntegerField(
        help_text="A ordem em que a pausa deve ser tirada (1 para a primeira, 2 para a segunda, etc.)"
    )
    duracao_minutos = models.PositiveIntegerField(
        help_text="A duração desta pausa específica em minutos."
    )

    class Meta:
        ordering = ["cargo", "ordem"]
        # Garante que não podemos ter duas "primeiras pausas" para o mesmo cargo
        unique_together = ("cargo", "ordem")
        verbose_name = "Regra de Pausa"
        verbose_name_plural = "Regras de Pausa"

    def __str__(self):
        return f"{self.cargo.nome} - Pausa #{self.ordem} ({self.duracao_minutos} min)"


class CentroDeCusto(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Banco(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


class Funcionario(models.Model):
    STATUS_OPERACIONAL_CHOICES = [
        ("DISPONIVEL", "Disponível"),
        ("EM_PAUSA", "Em Pausa"),
        ("OFFLINE", "Offline"),
    ]
    ESCOLARIDADE_CHOICES = [
        ("EF", "Ensino Fundamental"),
        ("EM", "Ensino Médio"),
        ("SI", "Superior Incompleto"),
        ("SC", "Superior Completo"),
        ("PG", "Pós-Graduação"),
    ]
    STATUS_CHOICES = [
        ("ATIVO", "Ativo"),
        ("FERIAS", "Férias"),
        ("AFASTADO", "Afastado"),
        ("DESLIGADO", "Desligado"),
    ]
    SEXO_CHOICES = [
        ("M", "Masculino"),
        ("F", "Feminino"),
        ("O", "Outro"),
        ("N", "Prefiro não dizer"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome_completo = models.CharField(max_length=255)
    deve_alterar_senha = models.BooleanField(default=True)
    data_nascimento = models.DateField()
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    telefone_celular = models.CharField(max_length=20, blank=True, null=True)
    email_pessoal = models.EmailField(
        max_length=255, unique=True, blank=True, null=True
    )
    escolaridade = models.CharField(
        max_length=2, choices=ESCOLARIDADE_CHOICES, blank=True, null=True
    )
    contato_emergencia_nome = models.CharField(max_length=255, blank=True, null=True)
    contato_emergencia_telefone = models.CharField(max_length=20, blank=True, null=True)
    data_contratacao = models.DateField()
    data_demissao = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ATIVO")
    status_operacional = models.CharField(
        max_length=20, choices=STATUS_OPERACIONAL_CHOICES, default="OFFLINE"
    )
    cep = models.CharField(max_length=9)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    cpf = BRCPFField(unique=True)
    rg = models.CharField(max_length=12)
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, null=True, blank=True)
    centro_de_custo = models.ForeignKey(
        CentroDeCusto, on_delete=models.SET_NULL, null=True, blank=True
    )
    supervisor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipe",
        help_text="O supervisor direto deste funcionário.",
    )
    banco = models.ForeignKey(Banco, on_delete=models.SET_NULL, null=True, blank=True)
    agencia = models.CharField(max_length=10)
    conta = models.CharField(max_length=15)

    def __str__(self):
        return self.nome_completo


class FuncionarioEscala(models.Model):
    """Associa um funcionário a uma escala por um período de tempo."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name="escalas"
    )
    escala = models.ForeignKey(Escala, on_delete=models.PROTECT)
    data_inicio = models.DateField()
    data_fim = models.DateField(
        null=True,
        blank=True,
        help_text="Deixe em branco se for a escala atual/permanente.",
    )

    class Meta:
        ordering = ["-data_inicio"]
        verbose_name = "Escala do Funcionário"
        verbose_name_plural = "Escalas dos Funcionários"

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.escala.nome} (a partir de {self.data_inicio})"


class BancoDeHoras(models.Model):
    """Registra o balanço de horas (créditos e débitos) para um funcionário."""

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name="banco_de_horas"
    )
    data = models.DateField()
    minutos = models.IntegerField(
        help_text="Minutos a serem creditados (positivo) ou debitados (negativo)."
    )
    descricao = models.CharField(
        max_length=255, help_text="Ex: Horas extras, Atraso, Saída antecipada."
    )
    processado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data"]
        verbose_name = "Registro de Banco de Horas"
        verbose_name_plural = "Registros de Banco de Horas"
        unique_together = ["funcionario", "data"]

    def __str__(self):
        status = "Crédito" if self.minutos > 0 else "Débito"
        return f"{self.funcionario.nome_completo}: {abs(self.minutos)} min ({status}) em {self.data}"


class SolicitacaoHorario(models.Model):
    """Registra um pedido de um funcionário para bater o ponto fora do horário permitido."""

    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("APROVADO", "Aprovado"),
        ("RECUSADO", "Recusado"),
    ]

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name="solicitacoes_horario"
    )
    data_hora_ponto = models.DateTimeField(
        help_text="Data e hora em que o funcionário deseja registrar o ponto."
    )
    motivo = models.TextField(max_length=500)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDENTE")

    # Quem e quando analisou a solicitação
    analisado_por = models.ForeignKey(
        Funcionario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_horario_analisadas",
    )
    data_analise = models.DateTimeField(null=True, blank=True)

    # Data de criação da solicitação
    data_solicitacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_solicitacao"]
        verbose_name = "Solicitação de Ponto Fora de Hora"
        verbose_name_plural = "Solicitações de Ponto Fora de Hora"

    def __str__(self):
        return f"Solicitação de {self.funcionario.nome_completo} para {self.data_hora_ponto.strftime('%d/%m/%Y %H:%M')}"


class SolicitacaoAlteracaoEndereco(models.Model):
    # ... (código sem alterações)
    STATUS_CHOICES = [("P", "Pendente"), ("A", "Aprovado"), ("R", "Recusado")]
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    cep = models.CharField(max_length=9)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=20)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P")
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Solicitação de Endereço de {self.funcionario.nome_completo}"


class SolicitacaoAlteracaoBancaria(models.Model):
    # ... (código sem alterações)
    STATUS_CHOICES = [("P", "Pendente"), ("A", "Aprovado"), ("R", "Recusado")]
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    banco = models.ForeignKey(Banco, on_delete=models.SET_NULL, null=True)
    agencia = models.CharField(max_length=10)
    conta = models.CharField(max_length=15)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default="P")
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Solicitação Bancária de {self.funcionario.nome_completo}"


class SolicitacaoAbono(models.Model):
    STATUS_CHOICES = [
        ("PENDENTE", "Pendente"),
        ("APROVADO", "Aprovado"),
        ("RECUSADO", "Recusado"),
    ]
    TIPO_ABONO_CHOICES = [
        ("FALTA", "Abono de Falta"),
        ("ATRASO", "Abono de Atraso/Horas"),
    ]

    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name="solicitacoes_abono"
    )
    tipo_abono = models.CharField(max_length=10, choices=TIPO_ABONO_CHOICES)
    data_inicio = models.DateTimeField(
        help_text="Data e hora de início do período a ser abonado"
    )
    data_fim = models.DateTimeField(
        help_text="Data e hora de fim do período a ser abonado"
    )
    motivo = models.TextField(max_length=500)
    documento = models.FileField(upload_to="documentos_abono/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDENTE")
    analisado_por = models.ForeignKey(
        Funcionario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitacoes_abono_analisadas",
    )
    data_analise = models.DateTimeField(null=True, blank=True)
    data_solicitacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_solicitacao"]
        verbose_name = "Solicitação de Abono"
        verbose_name_plural = "Solicitações de Abono"

    def __str__(self):
        return f"Solicitação de {self.funcionario.nome_completo} para {self.data_inicio.strftime('%d/%m/%Y')}"


class RegistroPonto(models.Model):
    # ... (código sem alterações)
    TIPO_REGISTRO_CHOICES = [
        ("ENTRADA", "Entrada"),
        ("SAIDA", "Saída"),
        ("SAIDA_PAUSA", "Saída para Pausa Programada"),
        ("VOLTA_PAUSA", "Volta da Pausa Programada"),
        ("SAIDA_PAUSA_PESSOAL", "Saída para Pausa Pessoal"),
        ("VOLTA_PAUSA_PESSOAL", "Volta da Pausa Pessoal"),
        ("SAIDA_ALMOCO", "Saída Almoço"),
        ("VOLTA_ALMOCO", "Volta Almoço"),
    ]
    funcionario = models.ForeignKey(
        Funcionario, on_delete=models.CASCADE, related_name="registros_ponto"
    )
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Data e Hora")
    tipo = models.CharField(max_length=30, choices=TIPO_REGISTRO_CHOICES)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Registro de Ponto"
        verbose_name_plural = "Registros de Ponto"

    def __str__(self):
        return f"{self.funcionario.nome_completo} - {self.get_tipo_display()} em {self.timestamp.strftime('%d/%m/%Y %H:%M:%S')}"