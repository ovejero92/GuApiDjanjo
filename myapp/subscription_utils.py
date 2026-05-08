"""Utilidades ligadas al plan / suscripción (evita código duplicado en views/middleware)."""
from django.conf import settings

from .models import Plan, Suscripcion


def ensure_suscripcion_gratuita(usuario):
    """
    Todo usuario debe tener una fila Suscripción (signals suelen crearla al alta).
    Cuentas creadas antes del seed de Plan o con fallos puntuales quedaban sin fila:
    crea gratis + activa.
    """
    if not usuario or not usuario.is_authenticated or not usuario.pk:
        return
    if Suscripcion.objects.filter(usuario_id=usuario.pk).exists():
        return
    try:
        plan = Plan.objects.only('id').get(slug='free')
    except Plan.DoesNotExist:
        return
    Suscripcion.objects.create(usuario=usuario, plan=plan, is_active=True)


def url_checkout_desde_respuesta_preapproval(response: dict):
    """
    Preferir sandbox cuando el Access Token es de pruebas, para evitar el error fatal
    del checkout público (/checkout/v1/subscription/.../fatal/).
    """
    token = (getattr(settings, 'MERCADOPAGO_ACCESS_TOKEN', '') or '').strip()
    if token.startswith('TEST'):
        url = response.get('sandbox_init_point')
        if url:
            return url
    return response.get('init_point') or response.get('sandbox_init_point')
