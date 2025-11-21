# funcionarios/management/commands/processar_pontos.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, datetime, time, date
from django.db import models
from funcionarios.models import (
    Funcionario,
    RegistroPonto,
    FuncionarioEscala,
    BancoDeHoras,
    SolicitacaoAbono,
    Feriado,
)
import holidays


class Command(BaseCommand):
    help = "Processa os registros de ponto para calcular o banco de horas dos funcionários."
    br_holidays = holidays.country_holidays("BR")

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Processa os pontos para uma data específica (formato: YYYY-MM-DD). Padrão: ontem.",
        )

    def eh_feriado(self, data_alvo):
        """Verifica se a data é um feriado nacional ou um feriado customizado."""
        # 1. Checa a biblioteca de feriados nacionais
        if data_alvo in self.br_holidays:
            return True

        # 2. Checa o modelo de feriados customizados (não recorrentes)
        if Feriado.objects.filter(data=data_alvo, recorrente=False).exists():
            return True

        # 3. Checa feriados customizados recorrentes
        if Feriado.objects.filter(
            data__day=data_alvo.day, data__month=data_alvo.month, recorrente=True
        ).exists():
            return True

        return False

    def handle(self, *args, **options):
        target_date_str = options["date"]
        if target_date_str:
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR("Formato de data inválido. Use YYYY-MM-DD.")
                )
                return
        else:
            target_date = timezone.now().date() - timedelta(days=1)

        self.stdout.write(
            f"Iniciando processamento de pontos para a data: {target_date.strftime('%d/%m/%Y')}..."
        )

        active_employees = Funcionario.objects.filter(status="ATIVO")

        for funcionario in active_employees:
            self.process_employee(funcionario, target_date)

        self.stdout.write(self.style.SUCCESS("Processamento concluído."))

    def process_employee(self, funcionario, target_date):
        # 0. Verificar se há abono de falta aprovado para o dia
        if SolicitacaoAbono.objects.filter(
            funcionario=funcionario,
            data_inicio__date=target_date,
            status="APROVADO",
            tipo_abono="FALTA",
        ).exists():
            self.stdout.write(
                f"  - [INFO] Dia com abono de falta aprovado para {funcionario.nome_completo}. Pulando..."
            )
            # Garante que o saldo para o dia seja zero, removendo qualquer registro pré-existente.
            BancoDeHoras.objects.filter(
                funcionario=funcionario, data=target_date
            ).delete()
            return

        # 1. Encontrar a escala do funcionário para o dia
        escala_info = FuncionarioEscala.objects.filter(
            funcionario=funcionario, data_inicio__lte=target_date
        ).filter(
            models.Q(data_fim__gte=target_date) | models.Q(data_fim__isnull=True)
        ).first()

        if not escala_info:
            self.stdout.write(
                f"  - [AVISO] Nenhuma escala encontrada para {funcionario.nome_completo} na data."
            )
            return

        escala = escala_info.escala

        # 2. Obter registros de ponto
        current_timezone = timezone.get_current_timezone()
        start_of_day_local = datetime.combine(
            target_date, time.min, tzinfo=current_timezone
        )
        end_of_day_local = datetime.combine(
            target_date, time.max, tzinfo=current_timezone
        )
        registros = RegistroPonto.objects.filter(
            funcionario=funcionario,
            timestamp__gte=start_of_day_local,
            timestamp__lte=end_of_day_local,
        ).order_by("timestamp")

        # 3. Lógica de feriado
        if self.eh_feriado(target_date):
            self.process_holiday(funcionario, target_date, escala, registros)
        else:
            self.process_normal_day(funcionario, target_date, escala, registros)
            
        # Garante que o status operacional seja OFFLINE para o próximo dia
        if funcionario.status_operacional != 'OFFLINE':
            funcionario.status_operacional = 'OFFLINE'
            funcionario.save(update_fields=['status_operacional'])
            self.stdout.write(f"  - [STATUS] Status operacional de {funcionario.nome_completo} definido para OFFLINE.")

    def process_holiday(self, funcionario, target_date, escala, registros):
        self.stdout.write(f"  - [INFO] Dia de feriado para {funcionario.nome_completo}.")
        jornada_liquida_minutos = self._calculate_jornada_liquida(registros)

        if escala.prioritaria:
            # Escala prioritária: Deve trabalhar, mas ganha 100% extra.
            entrada_esperada_obj = datetime.combine(target_date, escala.horario_entrada)
            saida_esperada_obj = datetime.combine(target_date, escala.horario_saida)
            if saida_esperada_obj < entrada_esperada_obj:
                saida_esperada_obj += timedelta(days=1)
            
            jornada_esperada_bruta = (saida_esperada_obj - entrada_esperada_obj).total_seconds() / 60
            almoco_esperado = escala.duracao_almoco_minutos if jornada_esperada_bruta > 300 else 0
            jornada_esperada_liquida = jornada_esperada_bruta - almoco_esperado

            if not registros.exists():
                # Falta em feriado em escala prioritária. Debita o dia.
                saldo_dia = -jornada_esperada_liquida
                descricao = "Falta em feriado (escala prioritária)"
                self.stdout.write(f"  - [FALTA] {funcionario.nome_completo}: {descricao}")
            else:
                # Trabalhou no feriado. Ganha 100% sobre as horas trabalhadas.
                saldo_dia = jornada_liquida_minutos + jornada_liquida_minutos - jornada_esperada_liquida
                descricao = "Trabalho em feriado (100%)"
                self.stdout.write(f"  - [OK] {funcionario.nome_completo}: {saldo_dia} min. ({descricao})")
        else:
            # Escala não prioritária: Folga no feriado, a menos que seja convocado.
            if not registros.exists():
                self.stdout.write(f"  - [INFO] Folga de feriado para {funcionario.nome_completo}. Sem processamento.")
                BancoDeHoras.objects.filter(funcionario=funcionario, data=target_date).delete()
                return 
            else:
                # Foi convocado e trabalhou. Ganha 100% das horas trabalhadas.
                saldo_dia = jornada_liquida_minutos * 2
                descricao = "Convocação em feriado (100%)"
                self.stdout.write(f"  - [OK] {funcionario.nome_completo}: {saldo_dia} min. ({descricao})")
        
        saldo_final_minutos = round(saldo_dia)
        if saldo_final_minutos != 0:
             BancoDeHoras.objects.update_or_create(
                funcionario=funcionario,
                data=target_date,
                defaults={'minutos': saldo_final_minutos, 'descricao': descricao}
            )
        else:
            # Limpa registro caso o saldo seja zero.
            BancoDeHoras.objects.filter(funcionario=funcionario, data=target_date).delete()


    def process_normal_day(self, funcionario, target_date, escala, registros):
        dia_da_semana = target_date.weekday()
        if str(dia_da_semana) not in escala.dias_semana.split(","):
            # TODO: Lógica para verificar se houve trabalho em dia de folga
            self.stdout.write(
                f"  - [INFO] Dia de folga para {funcionario.nome_completo}. Pulando..."
            )
            return

        if not registros.exists():
            self.stdout.write(
                f"  - [FALTA] Falta injustificada detectada para {funcionario.nome_completo}."
            )
            BancoDeHoras.objects.filter(
                funcionario=funcionario, data=target_date
            ).delete()
            return
        
        jornada_liquida_minutos = self._calculate_jornada_liquida(registros)

        entrada_esperada_obj = datetime.combine(target_date, escala.horario_entrada)
        saida_esperada_obj = datetime.combine(target_date, escala.horario_saida)

        if saida_esperada_obj < entrada_esperada_obj:  # Turno noturno
            saida_esperada_obj += timedelta(days=1)

        carga_horaria_bruta_esperada = (
            saida_esperada_obj - entrada_esperada_obj
        ).total_seconds() / 60

        almoco_a_descontar = 0
        if carga_horaria_bruta_esperada > 300:
            almoco_a_descontar = escala.duracao_almoco_minutos

        carga_horaria_liquida_esperada = (
            carga_horaria_bruta_esperada - almoco_a_descontar
        )

        diferenca_minutos = round(
            jornada_liquida_minutos - carga_horaria_liquida_esperada
        )

        if diferenca_minutos != 0:
            primeira_entrada = registros.filter(tipo="ENTRADA").first()
            descricao = "Ajuste"
            if primeira_entrada:
                descricao = self.get_description(
                    diferenca_minutos, primeira_entrada, escala.horario_entrada
                )

            BancoDeHoras.objects.update_or_create(
                funcionario=funcionario,
                data=target_date,
                defaults={"minutos": diferenca_minutos, "descricao": descricao},
            )
            self.stdout.write(
                f"  - [OK] {funcionario.nome_completo}: {diferenca_minutos} min. ({descricao})"
            )
        else:
            self.stdout.write(f"  - [OK] {funcionario.nome_completo}: Jornada cumprida.")

    def _calculate_jornada_liquida(self, registros):
        jornada_bruta_minutos = self._calculate_paired_duration(registros, "ENTRADA", "SAIDA")
        minutos_pausa = self._calculate_paired_duration(registros, "SAIDA_PAUSA", "VOLTA_PAUSA")
        minutos_almoco = self._calculate_paired_duration(registros, "SAIDA_ALMOCO", "VOLTA_ALMOCO")
        minutos_pausa_pessoal = self._calculate_paired_duration(registros, "SAIDA_PAUSA_PESSOAL", "VOLTA_PAUSA_PESSOAL")
        return jornada_bruta_minutos - minutos_pausa - minutos_almoco - minutos_pausa_pessoal

    def _calculate_paired_duration(self, registros, tipo_saida, tipo_volta):
        saidas = list(registros.filter(tipo=tipo_saida))
        voltas = list(registros.filter(tipo=tipo_volta))
        total_duration = timedelta()

        for s in saidas:
            corresponding_volta = next(
                (v for v in voltas if v.timestamp > s.timestamp), None
            )
            if corresponding_volta:
                total_duration += corresponding_volta.timestamp - s.timestamp
                voltas.remove(corresponding_volta)

        return total_duration.total_seconds() / 60

    def get_description(
        self, diferenca_minutos, entrada_real_obj, entrada_esperada_time
    ):
        local_timestamp = entrada_real_obj.timestamp.astimezone(
            timezone.get_current_timezone()
        )
        entrada_real_time = local_timestamp.time()

        atraso_minutos = (
            datetime.combine(date.today(), entrada_real_time)
            - datetime.combine(date.today(), entrada_esperada_time)
        ).total_seconds() / 60

        if atraso_minutos > 5:
            atraso_arredondado = round(atraso_minutos)
            if diferenca_minutos < 0 and (diferenca_minutos + atraso_arredondado) < -1:
                return f"Atraso ({atraso_arredondado} min) e Saída Antecipada"
            return f"Atraso de {atraso_arredondado} min"

        if diferenca_minutos > 0:
            return "Horas extras"
        elif diferenca_minutos < 0:
            return "Saída antecipada"

        return "Ajuste"
