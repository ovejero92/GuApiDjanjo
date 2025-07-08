from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from myapp.models import Turno
from django.conf import settings

class Command(BaseCommand):
    help = 'Envía recordatorios por email para los turnos del día siguiente.'

    def handle(self, *args, **kwargs):
        self.stdout.write("Iniciando el envío de recordatorios...")
        
        # Calculamos la fecha de mañana
        manana = timezone.localdate() + timedelta(days=1)
        
        # Buscamos turnos confirmados para mañana
        turnos_para_manana = Turno.objects.filter(
            fecha=manana,
            estado='confirmado'
        )

        if not turnos_para_manana.exists():
            self.stdout.write(self.style.SUCCESS("No hay turnos para mañana. No se enviarán correos."))
            return

        for turno in turnos_para_manana:
            cliente = turno.cliente
            if cliente.email:
                asunto = f"Recordatorio de tu turno en {turno.servicio.nombre}"
                mensaje = (
                    f"¡Hola, {cliente.first_name or cliente.username}!\n\n"
                    f"Te recordamos que tienes un turno mañana, {turno.fecha.strftime('%d/%m/%Y')}, "
                    f"a las {turno.hora.strftime('%H:%M')} en {turno.servicio.nombre}.\n\n"
                    f"Dirección: {turno.servicio.direccion}\n\n"
                    "¡Te esperamos!\n\n"
                    "El equipo de TurnosOnline."
                )
                
                try:
                    send_mail(
                        asunto,
                        mensaje,
                        settings.DEFAULT_FROM_EMAIL, # El email desde el que se envía
                        [cliente.email],            # La lista de destinatarios
                        fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Correo enviado a {cliente.email} para el turno {turno.id}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error al enviar correo para el turno {turno.id}: {e}"))
            else:
                self.stdout.write(self.style.WARNING(f"El cliente {cliente.username} del turno {turno.id} no tiene email."))

        self.stdout.write("Proceso de recordatorios finalizado.")