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
