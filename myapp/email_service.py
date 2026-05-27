"""
Envío de correos vía API Pidgeon con reintentos y registro en EmailFailureLog si falla.
No lanza excepciones hacia las vistas: fallos ⇒ log + False.

Soporta dos versiones de la API Pidgeon (ver https://github.com/ovejero92/pidgeon):
  • v1 (legacy): POST /send con `html` armado en Python.
  • v2 (recomendado): POST /v2/send con `templateId` + `templateData`. El HTML vive
    en Pidgeon (`src/v2/templates/*.html`) y queda registrado en su SQLite + webhook
    de Resend (estado real delivered/bounced).

El switch se controla con la setting `PIDGEON_API_VERSION` (`v2` por defecto). Cada
llamada acepta `template_id` + `template_data` y un `html` fallback; si v2 está
caído o el template no existe, reintenta con v1 + HTML para no perder el correo.

Los correos tras reservar turno se ejecutan en hilo tras on_commit para no bloquear
la respuesta HTTP si Pidgeon responde 502 o está lento (evita WORKER TIMEOUT en Gunicorn).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta
from functools import partial

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import close_old_connections, transaction
from django.utils import timezone

from .models import EmailFailureLog, Turno

logger = logging.getLogger(__name__)


def _pidgeon_base():
    return settings.PIDGEON_URL.rstrip('/')


def _pidgeon_version():
    """`v2` (default) o `v1`. Cualquier otro valor se trata como v1 por seguridad."""
    raw = str(getattr(settings, 'PIDGEON_API_VERSION', 'v2') or 'v2').lower().strip()
    return 'v2' if raw == 'v2' else 'v1'


def _wake_worker(base, timeout):
    """GET /health para reducir cold-starts del free tier de Render."""
    if not getattr(settings, 'PIDGEON_WAKE_BEFORE_SEND', True):
        return
    try:
        requests.get(f'{base}/health', timeout=min(8.0, float(timeout)))
        logger.debug('Pidgeon wake GET /health completado.')
    except requests.exceptions.RequestException as exc:
        logger.debug('Pidgeon wake omitido/falló (%s)', exc)


def _parse_success_response(data):
    """Extrae (messageId, logId) de una respuesta exitosa, tolerando esquemas v1/v2."""
    if not isinstance(data, dict):
        return 'ok', None
    message_id = (
        data.get('messageId')
        or data.get('message_id')
        or data.get('id')
        or 'ok'
    )
    log_id = data.get('logId') or data.get('log_id')
    return str(message_id), log_id


def _post_send(url, payload, timeout, attempts, event_type, to):
    """
    POST con reintentos breves. Devuelve (success, message_id_or_error, log_id, last_status).
    `last_status` = código HTTP del último intento (o None si nunca conectó); útil para decidir
    el fallback v2→v1 (404/400 ⇒ template inválido ⇒ no tiene sentido reintentar v1 con html).
    """
    error_msg = 'No se llegó a contactar el servicio.'
    last_status = None
    for attempt in range(attempts):
        try:
            logger.info(
                'Pidgeon POST %s intento=%s/%s destino=%s evento=%s',
                url, attempt + 1, attempts, to, event_type,
            )
            response = requests.post(url, json=payload, timeout=timeout)
            last_status = response.status_code
            if response.status_code == 200:
                try:
                    data = response.json()
                except ValueError:
                    data = None

                if isinstance(data, dict) and data.get('success') is False:
                    error_msg = str(data.get('error') or 'success=false en respuesta JSON')
                    logger.warning(
                        'Pidgeon HTTP 200 pero success=false (%s): %s', event_type, error_msg,
                    )
                else:
                    message_id, log_id = _parse_success_response(data)
                    logger.info(
                        'Email enviado a %s | evento=%s | messageId=%s | logId=%s',
                        to, event_type, message_id, log_id,
                    )
                    return True, message_id, log_id, last_status

            error_msg = f'HTTP {response.status_code}: {response.text[:2000]}'
            logger.warning(
                'Intento %s/%s falló (%s): %s', attempt + 1, attempts, event_type, error_msg,
            )
            # 4xx (template inválido, payload mal armado) no se arregla reintentando.
            if 400 <= response.status_code < 500:
                break
        except requests.exceptions.RequestException as exc:
            error_msg = str(exc)
            logger.warning(
                'Intento %s/%s falló (%s): %s', attempt + 1, attempts, event_type, error_msg,
            )

        # Backoff breve (no usar 2**n: bloqueaba el worker y Gunicorn mataba la petición con timeout).
        if attempt < attempts - 1:
            time.sleep(min(1.25, 0.2 + 0.25 * attempt))

    return False, error_msg, None, last_status


def send_email_via_pidgeon(
    to,
    subject,
    html,
    event_type,
    idempotency_key=None,
    max_retries=None,
    template_id=None,
    template_data=None,
):
    """
    Envía un email usando Pidgeon (v2 templates si está activado, con fallback transparente a v1).

    Args:
        to / subject: destinatario y asunto.
        html: HTML armado en Python. Se usa como fallback siempre.
        event_type: etiqueta interna para logs y EmailFailureLog (`verification`, etc.).
        idempotency_key: opcional, lo respeta Pidgeon (ventana 5 min).
        template_id / template_data: si están y PIDGEON_API_VERSION=v2, se manda a /v2/send.
            Si el endpoint v2 responde 4xx (template inexistente, payload inválido) se
            cae a v1 con `html`.

    Returns:
        (success: bool, message_id_or_error: str)
    """
    base = _pidgeon_base()
    if max_retries is None:
        attempts = max(1, int(getattr(settings, 'PIDGEON_SEND_ATTEMPTS', 4)))
    else:
        attempts = max_retries + 1
    timeout = getattr(settings, 'PIDGEON_TIMEOUT', 45)

    _wake_worker(base, timeout)

    use_v2 = _pidgeon_version() == 'v2' and template_id is not None
    v1_url = f'{base}/send'

    if use_v2:
        v2_url = f'{base}/v2/send'
        v2_payload = {
            'to': to,
            'subject': subject,
            'templateId': template_id,
            'templateData': template_data or {},
        }
        if idempotency_key:
            v2_payload['idempotencyKey'] = idempotency_key

        ok, info, log_id, last_status = _post_send(
            v2_url, v2_payload, timeout, attempts, event_type, to,
        )
        if ok:
            return True, info

        # Si el endpoint v2 devolvió 4xx (template mal nombrado, payload inválido)
        # o nunca conectó, no insistimos con v2 dentro del mismo request; probamos v1.
        # Si fue 5xx repetido, también caemos a v1: la prioridad es que el correo salga.
        logger.warning(
            'Pidgeon v2 falló (evento=%s, status=%s, msg=%s). Reintento con v1.',
            event_type, last_status, info,
        )

    # v1 (o fallback de v2)
    v1_payload = {'to': to, 'subject': subject, 'html': html}
    if idempotency_key:
        v1_payload['idempotencyKey'] = idempotency_key

    ok, info, _log_id, _last_status = _post_send(
        v1_url, v1_payload, timeout, attempts, event_type, to,
    )
    if ok:
        return True, info

    try:
        EmailFailureLog.objects.create(
            event_type=event_type,
            recipient=to,
            subject=subject,
            html_content=html,
            error_message=info[:10000],
            retry_count=attempts,
        )
    except Exception:
        logger.exception('No se pudo guardar EmailFailureLog para %s', to)

    logger.error('Email falló permanentemente a %s | evento=%s', to, event_type)
    return False, info


def send_email_with_fallback(
    to,
    subject,
    html,
    event_type,
    idempotency_key=None,
    template_id=None,
    template_data=None,
):
    """
    Wrapper que nunca propaga excepciones de red/HTTP hacia la vista.
    Mantengo la firma vieja + `template_id` / `template_data` opcionales para v2.
    """
    if not to:
        logger.warning('send_email_with_fallback omitido: destinatario vacío (%s)', event_type)
        return False
    try:
        success, _ = send_email_via_pidgeon(
            to,
            subject,
            html,
            event_type,
            idempotency_key=idempotency_key,
            template_id=template_id,
            template_data=template_data,
        )
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


def _fmt_fecha(turno):
    return turno.fecha.strftime('%d/%m/%Y')


def _fmt_hora(turno):
    return turno.hora.strftime('%H:%M')


def send_verification_email(user, request=None):
    token = create_verification_token_for_user(user)
    link = verification_link_for_token(token.token)
    nombre = (user.first_name or '').strip()
    subject = 'Verificá tu correo — TurnosOk'
    html = (
        f'<p>Hola{f" {nombre}" if nombre else ""},</p>'
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
        template_id='verificacion',
        template_data={
            'nombre': nombre or 'hola',
            'link': link,
            'producto': 'TurnosOk',
            'soporteEmail': 'soporte@turnosok.com',
        },
    )


def html_booking_confirmation_client(turno, prof_nombre, cancel_url):
    dur = turno.duracion_total
    fecha_s = _fmt_fecha(turno)
    hora_s = _fmt_hora(turno)
    return (
        f'<p>Tu solicitud de turno con <strong>{prof_nombre}</strong> en <strong>{turno.servicio.nombre}</strong> '
        f'quedó registrada.</p>'
        f'<p><strong>Fecha:</strong> {fecha_s}<br>'
        f'<strong>Hora:</strong> {hora_s}<br>'
        f'<strong>Duración:</strong> {dur} minutos<br>'
        f'<strong>Estado:</strong> pendiente de confirmación del profesional.</p>'
        f'<p><a href="{cancel_url}">Gestioná o cancelá desde «Mis turnos»</a></p>'
    )


def template_data_booking_pending_client(turno, prof_nombre, mis_turnos_url):
    return {
        'nombre': (turno.cliente.first_name or turno.cliente.email or '').strip() or 'hola',
        'negocio': turno.servicio.nombre,
        'profesional': prof_nombre,
        'servicio': turno.servicio.nombre,
        'fecha': _fmt_fecha(turno),
        'hora': _fmt_hora(turno),
        'duracion': str(turno.duracion_total),
        'misturnos_url': mis_turnos_url,
    }


def html_booking_notification_pro(turno, cliente_display, dash_url):
    fecha_s = _fmt_fecha(turno)
    hora_s = _fmt_hora(turno)
    return (
        '<p><strong>Nueva reserva</strong></p>'
        f'<p><strong>{cliente_display}</strong> solicitó un turno el {fecha_s} a las {hora_s}.</p>'
        f'<p>Servicio: {turno.servicio.nombre} — Duración: {turno.duracion_total} min.</p>'
        f'<p><a href="{dash_url}">Aceptá o rechazá desde tu panel</a></p>'
    )


def template_data_booking_pending_pro(turno, cliente_display, dashboard_url):
    return {
        'cliente': cliente_display,
        'servicio': turno.servicio.nombre,
        'fecha': _fmt_fecha(turno),
        'hora': _fmt_hora(turno),
        'duracion': str(turno.duracion_total),
        'dashboard_url': dashboard_url,
    }


def html_booking_accepted_client(turno, negocio_nombre, mis_turnos_url):
    fecha_s = _fmt_fecha(turno)
    hora_s = _fmt_hora(turno)
    return (
        f'<p>Tu turno en <strong>{negocio_nombre}</strong> fue <strong>confirmado</strong>.</p>'
        f'<p>{fecha_s} a las {hora_s}</p>'
        f'<p><a href="{mis_turnos_url}">Ver en Mis turnos</a></p>'
    )


def template_data_booking_accepted_client(turno, negocio_nombre, mis_turnos_url):
    return {
        'nombre': (turno.cliente.first_name or turno.cliente.email or '').strip() or 'hola',
        'negocio': negocio_nombre,
        'servicio': turno.servicio.nombre,
        'fecha': _fmt_fecha(turno),
        'hora': _fmt_hora(turno),
        'misturnos_url': mis_turnos_url,
    }


def html_booking_rejected_client(turno, negocio_nombre, servicio_url):
    return (
        f'<p>Tu solicitud de turno en <strong>{negocio_nombre}</strong> fue <strong>rechazada</strong>.</p>'
        '<p>Podés intentar otro horario cuando quieras.</p>'
        f'<p><a href="{servicio_url}">Volver al servicio para reagendar</a></p>'
    )


def template_data_booking_rejected_client(turno, negocio_nombre, servicio_url):
    return {
        'nombre': (turno.cliente.first_name or turno.cliente.email or '').strip() or 'hola',
        'negocio': negocio_nombre,
        'servicio_url': servicio_url,
    }


def html_booking_cancelled_owner(negocio_nombre, servicio_url):
    return (
        f'<p>Tu turno en <strong>{negocio_nombre}</strong> fue <strong>cancelado</strong>.</p>'
        f'<p><a href="{servicio_url}">Podés elegir otro horario desde el perfil del servicio</a></p>'
    )


def template_data_booking_cancelled_owner(cliente_first_name, negocio_nombre, servicio_url):
    return {
        'nombre': (cliente_first_name or '').strip() or 'hola',
        'negocio': negocio_nombre,
        'servicio_url': servicio_url,
    }


def html_reminder_client(turno, prof_nombre=None):
    return (
        f'<p>Tu turno es a las {_fmt_hora(turno)} el {_fmt_fecha(turno)}. '
        f'Servicio: {turno.servicio.nombre}.</p>'
    )


def template_data_reminder_client(turno, prof_nombre):
    return {
        'nombre': (turno.cliente.first_name or turno.cliente.email or '').strip() or 'hola',
        'profesional': prof_nombre,
        'servicio': turno.servicio.nombre,
        'fecha': _fmt_fecha(turno),
        'hora': _fmt_hora(turno),
    }


def html_reminder_pro(turno, cliente_nom, dashboard_url):
    return (
        f'<p>El turno con <strong>{cliente_nom}</strong> ({turno.servicio.nombre}) comienza a las '
        f'{_fmt_hora(turno)}.</p>'
        f'<p><a href="{dashboard_url}">Abrir tu panel</a></p>'
    )


def template_data_reminder_pro(turno, cliente_nom, dashboard_url):
    return {
        'cliente': cliente_nom,
        'servicio': turno.servicio.nombre,
        'fecha': _fmt_fecha(turno),
        'hora': _fmt_hora(turno),
        'dashboard_url': dashboard_url,
    }


def schedule_background(callable_fn):
    """
    Ejecuta callable_fn en un hilo tras el commit actual (para no bloquear Gunicorn
    ante Pidgeon lento / 502). Si falla callable_fn, sólo registra exception.
    """

    def _runner():
        close_old_connections()
        try:
            callable_fn()
        except Exception:
            logger.exception('Correos en segundo plano fallaron (callable interno)')
        finally:
            close_old_connections()

    transaction.on_commit(
        lambda: threading.Thread(target=_runner, daemon=True).start(),
    )


def schedule_turno_booking_emails(
    turno_id,
    cancel_url_abs,
    dashboard_url_abs,
    cliente_display,
    propietario_id,
):
    schedule_background(
        partial(
            dispatch_turno_booking_emails,
            turno_id,
            cancel_url_abs,
            dashboard_url_abs,
            cliente_display,
            propietario_id,
        )
    )


def dispatch_turno_booking_emails(
    turno_id,
    cancel_url_abs,
    dashboard_url_abs,
    cliente_display,
    propietario_id,
):
    """
    Llamar desde un hilo vía schedule_turno_booking_emails (o schedule_background).
    Relee el turno y el propietario.
    """
    try:
        turno = Turno.objects.select_related('servicio', 'profesional', 'cliente').get(pk=turno_id)
        propietario = User.objects.get(pk=propietario_id)
    except (Turno.DoesNotExist, User.DoesNotExist) as exc:
        logger.warning('Correos de reserva omitidos (%s)', exc)
        return

    cliente_email = (turno.cliente.email or '').strip()
    if cliente_email:
        prof_nombre = (
            turno.profesional.nombre if turno.profesional else turno.servicio.nombre
        )
        send_email_with_fallback(
            cliente_email,
            f'Turno confirmado con {prof_nombre}',
            html_booking_confirmation_client(turno, prof_nombre, cancel_url_abs),
            'booking_confirmation',
            idempotency_key=f'book-client-{turno.id}',
            template_id='turno-pendiente-cliente',
            template_data=template_data_booking_pending_client(
                turno, prof_nombre, cancel_url_abs,
            ),
        )

    if owner_receives_freelancer_emails(propietario):
        oe = (propietario.email or '').strip()
        if oe:
            send_email_with_fallback(
                oe,
                f'¡Nueva reserva! {cliente_display} solicitó un turno',
                html_booking_notification_pro(
                    turno,
                    cliente_display,
                    dashboard_url_abs,
                ),
                'booking_notification_pro',
                idempotency_key=f'book-pro-{turno.id}',
                template_id='turno-pendiente-pro',
                template_data=template_data_booking_pending_pro(
                    turno, cliente_display, dashboard_url_abs,
                ),
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
