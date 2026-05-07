"""Recordatorios ~15 min antes del inicio del turno (cliente siempre; propietario si plan ≠ free activo)."""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from myapp.email_service import (
    send_email_with_fallback,
    owner_receives_freelancer_emails,
    site_base_url,
)
from myapp.models import Turno


class Command(BaseCommand):
    help = 'Envía recordatorios 15±6 min antes de turnos confirmados (marcar recordatorio_enviado).'

    def handle(self, *args, **options):
        now = timezone.localtime()
        # Ventana para cron cada ~5 min: turno que empieza entre +10 y +22 minutos
        min_remaining = timedelta(minutes=10)
        max_remaining = timedelta(minutes=22)

        fecha_ini = (now + min_remaining).date()
        fecha_fin = (now + max_remaining).date()

        candidatos = (
            Turno.objects.filter(
                estado='confirmado',
                recordatorio_enviado=False,
                fecha__gte=fecha_ini,
                fecha__lte=fecha_fin,
            )
            .select_related('cliente', 'servicio', 'servicio__propietario', 'profesional')
            .iterator()
        )

        tz = timezone.get_current_timezone()
        sent = 0

        for turno in candidatos:
            inicio = turno.inicio_en_timezone(tz)
            delta_min = (inicio - now).total_seconds() / 60.0
            if delta_min < 10 or delta_min > 22:
                continue

            prof_nombre = (turno.profesional.nombre if turno.profesional else turno.servicio.nombre)
            cliente_nom = (
                turno.cliente.get_full_name()
                or turno.cliente.first_name
                or turno.cliente.email
            )

            send_email_with_fallback(
                turno.cliente.email,
                f'Recordatorio: tu turno con {prof_nombre} es en 15 minutos',
                f'<p>Tu turno es a las {turno.hora.strftime("%H:%M")} el {turno.fecha.strftime("%d/%m/%Y")}. '
                f'Servicio: {turno.servicio.nombre}.</p>',
                'reminder_client',
                idempotency_key=f'reminder-client-{turno.id}',
            )

            propietario = turno.servicio.propietario
            if owner_receives_freelancer_emails(propietario):
                dash_url = f'{site_base_url()}/dashboard/'
                send_email_with_fallback(
                    propietario.email,
                    f'Recordatorio: turno en 15 minutos con {cliente_nom}',
                    f'<p>El turno con <strong>{cliente_nom}</strong> ({turno.servicio.nombre}) comienza a las '
                    f'{turno.hora.strftime("%H:%M")}.</p>'
                    f'<p><a href="{dash_url}">Abrir tu panel</a></p>',
                    'reminder_pro',
                    idempotency_key=f'reminder-pro-{turno.id}',
                )

            Turno.objects.filter(pk=turno.pk).update(recordatorio_enviado=True)
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Procesados recordatorios: {sent}'))
