from .models import Suscripcion


def plan_sidebar_flags(request):
    """
    Alinea iconos del menú lateral con la misma regla que las vistas (is_active + flags del plan).
    """
    if not getattr(request, 'user', None).is_authenticated:
        return {}
    try:
        suscripcion = Suscripcion.objects.select_related('plan').get(usuario_id=request.user.pk)
    except Suscripcion.DoesNotExist:
        return {
            'plan_sidebar_metrics_locked': True,
            'plan_sidebar_apariencia_locked': True,
        }
    plan = suscripcion.plan
    if not plan:
        return {
            'plan_sidebar_metrics_locked': True,
            'plan_sidebar_apariencia_locked': True,
        }
    ok = suscripcion.is_active
    return {
        'plan_sidebar_metrics_locked': not (ok and plan.allow_metrics),
        'plan_sidebar_apariencia_locked': not (ok and plan.allow_customization),
    }


def dashboard_premium_celebration_flag(request):
    """
    mostrar_animacion: primera vez entrando al panel con plan de pago activo,
    antes de guardar ha_visto_animacion_premium (se marca por POST tras el overlay).
    """
    path = getattr(request, 'path', '') or ''
    if (
        not getattr(request, 'user', None).is_authenticated
        or not path.startswith('/dashboard')
    ):
        return {'mostrar_animacion': False}
    try:
        suscripcion = Suscripcion.objects.select_related('plan').get(
            usuario_id=request.user.pk
        )
        plan = suscripcion.plan
        mostrar_animacion = bool(
            suscripcion.is_active
            and plan
            and plan.slug != 'free'
            and not suscripcion.ha_visto_animacion_premium
        )
    except Suscripcion.DoesNotExist:
        mostrar_animacion = False
    return {'mostrar_animacion': mostrar_animacion}
