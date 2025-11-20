
# funcionarios/management/commands/processar_pontos.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime, time, date
from django.db import models
from funcionarios.models import Funcionario, RegistroPonto, FuncionarioEscala, BancoDeHoras, SolicitacaoAbono

class Command(BaseCommand):
    help = "Processa os registros de ponto para calcular o banco de horas dos funcionários."

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Processa os pontos para uma data específica (formato: YYYY-MM-DD). Padrão: ontem.'
        )

    def handle(self, *args, **options):
        target_date_str = options['date']
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(self.style.ERROR("Formato de data inválido. Use YYYY-MM-DD."))
                return
        else:
            target_date = timezone.now().date() - timedelta(days=1)

        self.stdout.write(f"Iniciando processamento de pontos para a data: {target_date.strftime('%d/%m/%Y')}...")

        active_employees = Funcionario.objects.filter(status='ATIVO')

        for funcionario in active_employees:
            self.process_employee(funcionario, target_date)

        self.stdout.write(self.style.SUCCESS("Processamento concluído."))

    def process_employee(self, funcionario, target_date):
        # 0. Verificar se há abono de falta aprovado para o dia
        if SolicitacaoAbono.objects.filter(
            funcionario=funcionario,
            data_inicio__date=target_date,
            status='APROVADO',
            tipo_abono='FALTA'
        ).exists():
            self.stdout.write(f"  - [INFO] Dia com abono de falta aprovado para {funcionario.nome_completo}. Pulando...")
            # Garante que o saldo para o dia seja zero, removendo qualquer registro pré-existente.
            BancoDeHoras.objects.filter(funcionario=funcionario, data=target_date).delete()
            return

        # 1. Encontrar a escala do funcionário para o dia
        escala_info = FuncionarioEscala.objects.filter(
            funcionario=funcionario,
            data_inicio__lte=target_date
        ).filter(
            models.Q(data_fim__gte=target_date) | models.Q(data_fim__isnull=True)
        ).first()

        if not escala_info:
            self.stdout.write(f"  - [AVISO] Nenhuma escala encontrada para {funcionario.nome_completo} na data.")
            return

        escala = escala_info.escala
        dia_da_semana = target_date.weekday() # Segunda = 0, Domingo = 6

        if str(dia_da_semana) not in escala.dias_semana.split(','):
            # TODO: Lógica para verificar se houve trabalho em dia de folga
            self.stdout.write(f"  - [INFO] Dia de folga para {funcionario.nome_completo}. Pulando...")
            return

        # 2. Obter registros de ponto do dia
        registros = RegistroPonto.objects.filter(
            funcionario=funcionario,
            timestamp__date=target_date
        ).order_by('timestamp')

        if not registros.exists():
            # Lógica para falta injustificada
            # Se for um dia de trabalho e não há registros, é uma falta.
            carga_horaria_bruta_esperada = (
                datetime.combine(target_date, escala.horario_saida) - 
                datetime.combine(target_date, escala.horario_entrada)
            ).total_seconds() / 60
            
            if escala.horario_saida < escala.horario_entrada: # Turno noturno
                carga_horaria_bruta_esperada += 24 * 60

            carga_horaria_liquida_esperada = carga_horaria_bruta_esperada - escala.duracao_almoco_minutos
            
            # Cria o registro negativo no banco de horas
            BancoDeHoras.objects.update_or_create(
                funcionario=funcionario,
                data=target_date,
                defaults={
                    'minutos': -carga_horaria_bruta_esperada,
                    'descricao': 'Falta Injustificada'
                }
            )
            self.stdout.write(f"  - [FALTA] Falta injustificada para {funcionario.nome_completo}.")
            return

        # 3. Calcular horas trabalhadas e pausas
        entrada = registros.filter(tipo='ENTRADA').first()
        saida = registros.filter(tipo='SAIDA').last()

        if not entrada or not saida:
            self.stdout.write(f"  - [ERRO] Falta registro de ENTRADA ou SAIDA para {funcionario.nome_completo}.")
            return

        jornada_bruta_minutos = (saida.timestamp - entrada.timestamp).total_seconds() / 60

        # Calcular pausas
        minutos_pausa = self.calculate_break_time(registros, 'SAIDA_PAUSA', 'VOLTA_PAUSA')
        minutos_almoco = self.calculate_break_time(registros, 'SAIDA_ALMOCO', 'VOLTA_ALMOCO')
        
        jornada_liquida_minutos = jornada_bruta_minutos - minutos_pausa - minutos_almoco

        # 4. Calcular carga horária esperada
        entrada_esperada = datetime.combine(target_date, escala.horario_entrada)
        saida_esperada = datetime.combine(target_date, escala.horario_saida)
        
        if saida_esperada < entrada_esperada: # Turno noturno
            saida_esperada += timedelta(days=1)

        carga_horaria_bruta_esperada = (saida_esperada - entrada_esperada).total_seconds() / 60
        carga_horaria_liquida_esperada = carga_horaria_bruta_esperada - escala.duracao_almoco_minutos

        # 5. Calcular diferença e criar registro no banco de horas
        diferenca_minutos = round(jornada_liquida_minutos - carga_horaria_liquida_esperada)

        if diferenca_minutos != 0:
            descricao = self.get_description(diferenca_minutos, entrada, entrada_esperada.time())
            
            BancoDeHoras.objects.update_or_create(
                funcionario=funcionario,
                data=target_date,
                defaults={'minutos': diferenca_minutos, 'descricao': descricao}
            )
            self.stdout.write(f"  - [OK] {funcionario.nome_completo}: {diferenca_minutos} min. ({descricao})")
        else:
            self.stdout.write(f"  - [OK] {funcionario.nome_completo}: Jornada cumprida.")

        # Ao final do processamento do dia, garante que o status operacional volte a ser OFFLINE
        if funcionario.status_operacional != 'OFFLINE':
            funcionario.status_operacional = 'OFFLINE'
            funcionario.save(update_fields=['status_operacional'])
            self.stdout.write(f"  - [STATUS] Status operacional de {funcionario.nome_completo} definido para OFFLINE.")

    def calculate_break_time(self, registros, tipo_saida, tipo_volta):
        saidas = list(registros.filter(tipo=tipo_saida))
        voltas = list(registros.filter(tipo=tipo_volta))
        total_break_time = timedelta()

        for s in saidas:
            # Encontra a primeira volta correspondente após a saída
            corresponding_volta = next((v for v in voltas if v.timestamp > s.timestamp), None)
            if corresponding_volta:
                total_break_time += corresponding_volta.timestamp - s.timestamp
                voltas.remove(corresponding_volta) # Evita que a mesma volta seja usada duas vezes
        
        return total_break_time.total_seconds() / 60

    def get_description(self, diferenca_minutos, entrada_real_obj, entrada_esperada_time):
        # Lógica simples para descrição
        entrada_real_time = entrada_real_obj.timestamp.time()
        atraso_minutos = (datetime.combine(date.today(), entrada_real_time) - datetime.combine(date.today(), entrada_esperada_time)).total_seconds() / 60

        if atraso_minutos > 5: # Tolerância de 5 minutos
            return f"Atraso de {round(atraso_minutos)} min"
        
        if diferenca_minutos > 0:
            return "Horas extras"
        elif diferenca_minutos < 0:
            return "Saída antecipada"
        
        return "Ajuste"
