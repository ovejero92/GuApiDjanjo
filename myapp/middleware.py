# myapp/middleware.py
from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django.urls import reverse
from allauth.socialaccount.models import SocialAccount

from .subscription_utils import ensure_suscripcion_gratuita


class EnsureSuscripcionGratuitaMiddleware:
    """
    Completa Suscripción gratuita ausente en cualquier página de la sesión iniciada,
    menos admin y ficheros estáticos.
    Debe ejecutarse después de AuthenticationMiddleware.
    """

    SKIP_PREFIXES = (
        '/admin/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            getattr(request, 'user', None).is_authenticated
            and all(not request.path.startswith(p) for p in self.SKIP_PREFIXES)
        ):
            ensure_suscripcion_gratuita(request.user)
        return self.get_response(request)


class RequireVerifiedEmailMiddleware:
    """
    Refuerzo frente al login con email/contraseña si allauth omitiera CustomLoginForm
    en algún flujo: sesión válida pero perfil.email_verificado=False → logout.
    Rutas públicas como /accounts/*, verificación y admin quedan exentas.
    """

    EXEMPT_PREFIXES = (
        '/admin/',
        '/accounts/',
        '/static/',
        '/media/',
        '/verify-email/',
        '/resend-verification-email/',
        '/internal/cron/',
        '/sitemap.xml',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path
            if path.startswith(self.EXEMPT_PREFIXES):
                return self.get_response(request)
            if request.user.is_superuser:
                return self.get_response(request)
            if SocialAccount.objects.filter(user=request.user).exists():
                return self.get_response(request)
            try:
                verified = request.user.perfil.email_verified
            except ObjectDoesNotExist:
                verified = False
            if not verified:
                auth_logout(request)
                messages.info(
                    request,
                    'Debés verificar tu correo antes de usar la cuenta. '
                    'Podés solicitar otro correo desde el enlace «¿No recibiste el correo de verificación?» en iniciar sesión.',
                )
                return redirect(reverse('account_login'))
        return self.get_response(request)
