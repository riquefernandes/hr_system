
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

        # 2. Obter registros de ponto do dia (usando filtro de intervalo de tempo localizado)
        current_timezone = timezone.get_current_timezone()
        start_of_day_local = datetime.combine(target_date, time.min, tzinfo=current_timezone)
        end_of_day_local = datetime.combine(target_date, time.max, tzinfo=current_timezone)

        registros = RegistroPonto.objects.filter(
            funcionario=funcionario,
            timestamp__gte=start_of_day_local,
            timestamp__lte=end_of_day_local
        ).order_by('timestamp')
        


        if not registros.exists():
            # Lógica para falta injustificada: Apenas registra a ocorrência, não debita do banco de horas.
            self.stdout.write(f"  - [FALTA] Falta injustificada detectada para {funcionario.nome_completo}.")
            
            # Limpa qualquer registro de BH que possa ter sido criado erroneamente em execuções anteriores
            BancoDeHoras.objects.filter(funcionario=funcionario, data=target_date).delete()

            # Garante que o status operacional seja OFFLINE para o próximo dia
            if funcionario.status_operacional != 'OFFLINE':
                funcionario.status_operacional = 'OFFLINE'
                funcionario.save(update_fields=['status_operacional'])
                self.stdout.write(f"  - [STATUS] Status operacional de {funcionario.nome_completo} definido para OFFLINE.")
            return

        # 3. Calcular horas trabalhadas e pausas
        jornada_bruta_minutos = self._calculate_paired_duration(registros, 'ENTRADA', 'SAIDA')

        minutos_pausa = self._calculate_paired_duration(registros, 'SAIDA_PAUSA', 'VOLTA_PAUSA')
        minutos_almoco = self._calculate_paired_duration(registros, 'SAIDA_ALMOCO', 'VOLTA_ALMOCO')
        minutos_pausa_pessoal = self._calculate_paired_duration(registros, 'SAIDA_PAUSA_PESSOAL', 'VOLTA_PAUSA_PESSOAL')
        
        jornada_liquida_minutos = jornada_bruta_minutos - minutos_pausa - minutos_almoco - minutos_pausa_pessoal

        # 4. Calcular carga horária esperada
        entrada_esperada_obj = datetime.combine(target_date, escala.horario_entrada)
        saida_esperada_obj = datetime.combine(target_date, escala.horario_saida)
        
        if saida_esperada_obj < entrada_esperada_obj: # Turno noturno
            saida_esperada_obj += timedelta(days=1)

        carga_horaria_bruta_esperada = (saida_esperada_obj - entrada_esperada_obj).total_seconds() / 60
        
        almoco_a_descontar = 0
        if carga_horaria_bruta_esperada > 300:
            almoco_a_descontar = escala.duracao_almoco_minutos

        carga_horaria_liquida_esperada = carga_horaria_bruta_esperada - almoco_a_descontar

        # 5. Calcular diferença e criar registro no banco de horas
        diferenca_minutos = round(jornada_liquida_minutos - carga_horaria_liquida_esperada)

        if diferenca_minutos != 0:
            primeira_entrada = registros.filter(tipo='ENTRADA').first()
            descricao = "Ajuste"
            if primeira_entrada:
                 descricao = self.get_description(diferenca_minutos, primeira_entrada, escala.horario_entrada)
            
            BancoDeHoras.objects.update_or_create(
                funcionario=funcionario,
                data=target_date,
                defaults={'minutos': diferenca_minutos, 'descricao': descricao}
            )
            self.stdout.write(f"  - [OK] {funcionario.nome_completo}: {diferenca_minutos} min. ({descricao})")
        else:
            self.stdout.write(f"  - [OK] {funcionario.nome_completo}: Jornada cumprida.")
        
        if funcionario.status_operacional != 'OFFLINE':
            funcionario.status_operacional = 'OFFLINE'
            funcionario.save(update_fields=['status_operacional'])
            self.stdout.write(f"  - [STATUS] Status operacional de {funcionario.nome_completo} definido para OFFLINE.")

    def _calculate_paired_duration(self, registros, tipo_saida, tipo_volta):
        saidas = list(registros.filter(tipo=tipo_saida))
        voltas = list(registros.filter(tipo=tipo_volta))
        total_duration = timedelta()

        for s in saidas:
            corresponding_volta = next((v for v in voltas if v.timestamp > s.timestamp), None)
            if corresponding_volta:
                total_duration += corresponding_volta.timestamp - s.timestamp
                voltas.remove(corresponding_volta)
        
        return total_duration.total_seconds() / 60

    def get_description(self, diferenca_minutos, entrada_real_obj, entrada_esperada_time):
        local_timestamp = entrada_real_obj.timestamp.astimezone(timezone.get_current_timezone())
        entrada_real_time = local_timestamp.time()
        
        atraso_minutos = (datetime.combine(date.today(), entrada_real_time) - datetime.combine(date.today(), entrada_esperada_time)).total_seconds() / 60

        if atraso_minutos > 5:
            atraso_arredondado = round(atraso_minutos)
            # Verifica se o déficit é maior que apenas o atraso (indicando saída antecipada também)
            if diferenca_minutos < 0 and (diferenca_minutos + atraso_arredondado) < -1:
                 return f"Atraso ({atraso_arredondado} min) e Saída Antecipada"
            return f"Atraso de {atraso_arredondado} min"
        
        if diferenca_minutos > 0:
            return "Horas extras"
        elif diferenca_minutos < 0:
            return "Saída antecipada"
        
        return "Ajuste"
