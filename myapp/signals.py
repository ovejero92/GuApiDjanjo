from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_added

from .models import Plan, Suscripcion
from .email_service import send_verification_email


@receiver(post_save, sender=User)
def crear_suscripcion_gratuita(sender, instance, created, **kwargs):
    if created:
        try:
            plan_gratuito = Plan.objects.get(slug='free')
            Suscripcion.objects.get_or_create(usuario=instance, defaults={'plan': plan_gratuito, 'is_active': True})
        except Plan.DoesNotExist:
            pass


@receiver(user_signed_up)
def send_email_verification_pidgeon(sender, request, user, **kwargs):
    """Registro con email/contraseña: verificación vía Pidgeon (fallback transparente)."""
    from .models import PerfilUsuario

    PerfilUsuario.objects.get_or_create(usuario=user)

    if SocialAccount.objects.filter(user=user).exists():
        return
    try:
        user.perfil.email_verified = False
        user.perfil.save(update_fields=['email_verified'])
    except Exception:
        pass
    send_verification_email(user, request)
    if request is not None:
        from django.contrib import messages as dj_messages

        dj_messages.success(
            request,
            'Te enviamos un correo para verificar tu cuenta. Cuando hagas clic en el enlace, '
            'podrás iniciar sesión.',
        )


@receiver(social_account_added)
def mark_oauth_user_email_verified(request, sociallogin, **kwargs):
    from .models import PerfilUsuario

    user = sociallogin.user
    PerfilUsuario.objects.get_or_create(usuario=user)
    perfil = getattr(user, 'perfil', None)
    if perfil is None:
        return
    if not perfil.email_verified:
        perfil.email_verified = True
        perfil.save(update_fields=['email_verified'])
