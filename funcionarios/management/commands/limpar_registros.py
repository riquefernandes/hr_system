from django.core.management.base import BaseCommand
from funcionarios.models import RegistroPonto, BancoDeHoras, Funcionario

class Command(BaseCommand):
    help = "Exclui todos os registros de ponto, banco de horas e reseta o status operacional dos funcionários."

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirma a execução do comando para deletar todos os dados.',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                "ATENÇÃO: Este comando é destrutivo e irá deletar todos os registros de ponto e banco de horas."
            ))
            self.stdout.write(self.style.WARNING(
                "Para confirmar a execução, rode o comando novamente com a flag --confirm:"
            ))
            self.stdout.write(self.style.SUCCESS(
                "python manage.py limpar_registros --confirm"
            ))
            return

        self.stdout.write(self.style.HTTP_INFO("Deletando todos os registros de ponto..."))
        count_rp, _ = RegistroPonto.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"--> {count_rp} registros de ponto foram deletados."))

        self.stdout.write(self.style.HTTP_INFO("Deletando todos os registros de banco de horas..."))
        count_bh, _ = BancoDeHoras.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"--> {count_bh} registros de banco de horas foram deletados."))

        self.stdout.write(self.style.HTTP_INFO("Resetando status operacional de todos os funcionários para 'OFFLINE'..."))
        count_func = Funcionario.objects.update(status_operacional='OFFLINE')
        self.stdout.write(self.style.SUCCESS(f"--> {count_func} funcionários foram atualizados."))

        self.stdout.write(self.style.SUCCESS("\nOperação concluída! O sistema está em um estado limpo para novos testes."))
