"""
Envío de correos vía API Pidgeon con reintentos y registro en EmailFailureLog si falla.
No lanza excepciones hacia las vistas: fallos ⇒ log + False.
"""
from __future__ import annotations

import logging
import time
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import EmailFailureLog

logger = logging.getLogger(__name__)


def send_email_via_pidgeon(to, subject, html, event_type, idempotency_key=None, max_retries=None):
    """
    Envía un email usando Pidgeon con reintentos exponenciales.
    Retorna (success: bool, message_id_or_error: str).
    """
    base = settings.PIDGEON_URL.rstrip('/')
    url = f'{base}/send'
    payload = {'to': to, 'subject': subject, 'html': html}
    if idempotency_key:
        payload['idempotencyKey'] = idempotency_key

    error_msg = 'No se llegó a contactar el servicio.'
    if max_retries is None:
        attempts = max(1, int(getattr(settings, 'PIDGEON_SEND_ATTEMPTS', 4)))
    else:
        attempts = max_retries + 1
    timeout = getattr(settings, 'PIDGEON_TIMEOUT', 45)

    for attempt in range(attempts):
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            if response.status_code == 200:
                body = ''
                mid = 'ok'
                try:
                    data = response.json()
                    mid = data.get('messageId') or data.get('message_id') or 'ok'
                except ValueError:
                    body = response.text[:500]
                    mid = body or 'ok'
                logger.info('Email enviado a %s | evento=%s | id=%s', to, event_type, mid)
                return True, str(mid)

            error_msg = f'HTTP {response.status_code}: {response.text[:2000]}'
            logger.warning('Intento %s/%s falló (%s): %s', attempt + 1, attempts, event_type, error_msg)
        except requests.exceptions.RequestException as exc:
            error_msg = str(exc)
            logger.warning('Intento %s/%s falló (%s): %s', attempt + 1, attempts, event_type, error_msg)

        if attempt < attempts - 1:
            time.sleep(2**attempt)

    try:
        EmailFailureLog.objects.create(
            event_type=event_type,
            recipient=to,
            subject=subject,
            html_content=html,
            error_message=error_msg[:10000],
            retry_count=attempts,
        )
    except Exception:
        logger.exception('No se pudo guardar EmailFailureLog para %s', to)

    logger.error('Email falló permanentemente a %s | evento=%s', to, event_type)
    return False, error_msg


def send_email_with_fallback(to, subject, html, event_type, idempotency_key=None):
    """
    Wrapper que nunca propaga excepciones de red/HTTP hacia la vista.
    """
    if not to:
        logger.warning('send_email_with_fallback omitido: destinatario vacío (%s)', event_type)
        return False
    try:
        success, _ = send_email_via_pidgeon(to, subject, html, event_type, idempotency_key=idempotency_key)
        return success
    except Exception as exc:
        logger.exception('Error inesperado en send_email_with_fallback: %s', exc)
        try:
            EmailFailureLog.objects.create(
                event_type=event_type,
                recipient=to,
                subject=subject,
                html_content=html,
                error_message=str(exc)[:10000],
                retry_count=0,
            )
        except Exception:
            pass
        return False


def site_base_url():
    return getattr(settings, 'SITE_BASE_URL', 'https://turnosok.com').rstrip('/')


def verification_link_for_token(token_uuid):
    return f'{site_base_url()}/verify-email/{token_uuid}/'


def mis_turnos_link(request=None):
    if request:
        return request.build_absolute_uri('/mis-turnos/')
    return f'{site_base_url()}/mis-turnos/'


def dashboard_turnos_link(request=None):
    if request:
        return request.build_absolute_uri('/dashboard/')
    return f'{site_base_url()}/dashboard/'


def create_verification_token_for_user(user):
    from .models import EmailVerificationToken

    EmailVerificationToken.objects.filter(user=user).delete()
    return EmailVerificationToken.objects.create(
        user=user,
        expires_at=timezone.now() + timedelta(hours=24),
    )


def send_verification_email(user, request=None):
    token = create_verification_token_for_user(user)
    link = verification_link_for_token(token.token)
    subject = 'Verificá tu correo — TurnosOk'
    html = (
        f'<p>Hola{f" {user.first_name}" if user.first_name else ""},</p>'
        '<p>Hacé clic en el siguiente enlace para verificar tu cuenta (válido 24 horas):</p>'
        f'<p><a href="{link}">{link}</a></p>'
        '<p>Si no creaste una cuenta en TurnosOk, ignorá este mensaje.</p>'
    )
    return send_email_with_fallback(
        user.email,
        subject,
        html,
        'verification',
        idempotency_key=f'verify-{user.id}-{token.token}',
    )


def html_booking_confirmation_client(turno, prof_nombre, cancel_url):
    dur = turno.duracion_total
    fecha_s = turno.fecha.strftime('%d/%m/%Y')
    hora_s = turno.hora.strftime('%H:%M')
    return (
        f'<p>Tu solicitud de turno con <strong>{prof_nombre}</strong> en <strong>{turno.servicio.nombre}</strong> '
        f'quedó registrada.</p>'
        f'<p><strong>Fecha:</strong> {fecha_s}<br>'
        f'<strong>Hora:</strong> {hora_s}<br>'
        f'<strong>Duración:</strong> {dur} minutos<br>'
        f'<strong>Estado:</strong> pendiente de confirmación del profesional.</p>'
        f'<p><a href="{cancel_url}">Gestioná o cancelá desde «Mis turnos»</a></p>'
    )


def html_booking_notification_pro(turno, cliente_display, dash_url):
    fecha_s = turno.fecha.strftime('%d/%m/%Y')
    hora_s = turno.hora.strftime('%H:%M')
    return (
        '<p><strong>Nueva reserva</strong></p>'
        f'<p><strong>{cliente_display}</strong> solicitó un turno el {fecha_s} a las {hora_s}.</p>'
        f'<p>Servicio: {turno.servicio.nombre} — Duración: {turno.duracion_total} min.</p>'
        f'<p><a href="{dash_url}">Aceptá o rechazá desde tu panel</a></p>'
    )


def html_booking_accepted_client(turno, negocio_nombre, mis_turnos_url):
    fecha_s = turno.fecha.strftime('%d/%m/%Y')
    hora_s = turno.hora.strftime('%H:%M')
    return (
        f'<p>Tu turno en <strong>{negocio_nombre}</strong> fue <strong>confirmado</strong>.</p>'
        f'<p>{fecha_s} a las {hora_s}</p>'
        f'<p><a href="{mis_turnos_url}">Ver en Mis turnos</a></p>'
    )


def html_booking_rejected_client(turno, negocio_nombre, servicio_url):
    return (
        f'<p>Tu solicitud de turno en <strong>{negocio_nombre}</strong> fue <strong>rechazada</strong>.</p>'
        '<p>Podés intentar otro horario cuando quieras.</p>'
        f'<p><a href="{servicio_url}">Volver al servicio para reagendar</a></p>'
    )


def owner_receives_freelancer_emails(owner_user):
    """Plan Free: sin emails al freelancer/propietario. Pro/Prime activos: sí."""
    try:
        sus = owner_user.suscripcion
        if not sus.is_active or not sus.plan_id:
            return False
        return sus.plan.slug != 'free'
    except Exception:
        return False
