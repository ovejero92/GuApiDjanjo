import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.urls import reverse
from allauth.account.adapter import DefaultAccountAdapter

from myapp.signup_email_policy import DISPOSABLE_EMAIL_DOMAINS

logger = logging.getLogger(__name__)

_MAIL_SEND_FAIL_MSG = (
    "No pudimos enviar el correo de verificación desde el servidor. "
    "En planes gratuitos Render bloquea el envío SMTP: creá una API key de SendGrid y "
    "configurá la variable SENDGRID_API_KEY en Render, o bien subí a un plan de pago. "
    "Tu cuenta igual puede haberse creado: probá iniciar sesión."
)


class MyAccountAdapter(DefaultAccountAdapter):
    """
    - send_mail: evita que un fallo de SMTP tumbe Gunicorn cuando vuelvas a
      ACCOUNT_EMAIL_VERIFICATION='mandatory' y el envío falle.
    - clean_email: filtra dominios desechables (no valida propiedad del buzón).
    """

    def clean_email(self, email):
        email = super().clean_email(email)
        if not email:
            return email
        if not getattr(settings, 'BLOCK_DISPOSABLE_SIGNUP_EMAILS', True):
            return email
        domain = email.rpartition('@')[2].lower()
        if domain in DISPOSABLE_EMAIL_DOMAINS:
            raise ValidationError(
                'Usá un correo personal o de trabajo; no se permiten servicios de email temporal.'
            )
        return email

    def send_mail(self, template_prefix, email, context):
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception:
            logger.exception(
                "Fallo al enviar correo allauth (plantilla=%s, destino=%s)",
                template_prefix,
                email,
            )
            request = getattr(self, 'request', None)
            if request is not None:
                messages.warning(request, _MAIL_SEND_FAIL_MSG)
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