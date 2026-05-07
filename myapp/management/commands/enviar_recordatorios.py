from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Delegado a send_reminders (recordatorio ~15 min antes). El comando antiguo por día ya no se usa.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Delegando a send_reminders…'))
        call_command('send_reminders')
