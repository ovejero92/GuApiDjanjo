import logging

from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

logger = logging.getLogger(__name__)


class MyAccountAdapter(DefaultAccountAdapter):
    """
    Evita que un fallo de SMTP (p. ej. credenciales o red en Render) derribe el worker
    de Gunicorn durante registro, verificación o avisos de «cuenta ya existe».
    """

    def send_mail(self, template_prefix, email, context):
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception:
            logger.exception(
                "Fallo al enviar correo allauth (plantilla=%s, destino=%s)",
                template_prefix,
                email,
            )
            return None

    def get_login_redirect_url(self, request):
        next_url = request.GET.get('next')
        if next_url:
            return next_url

        if request.user.servicios_propios.exists():
            path = reverse('dashboard_propietario')
        else:
            path = reverse('index')
        
        return path