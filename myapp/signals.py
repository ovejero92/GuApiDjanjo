import logging
import threading

from django.contrib.auth.models import User
from django.db import close_old_connections, transaction
from django.dispatch import receiver
from django.db.models.signals import post_save

from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.signals import social_account_added

from .models import Plan, Suscripcion
from .email_service import send_verification_email

logger = logging.getLogger(__name__)


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

    user_id = user.pk

    def _send_after_commit():
        def _runner():
            close_old_connections()
            try:
                u = User.objects.get(pk=user_id)
                send_verification_email(u, None)
            except User.DoesNotExist:
                logger.warning('Usuario %s ya no existe tras commit; no se envía verificación', user_id)
            except Exception:
                logger.exception('Envío en segundo plano del correo de verificación falló (user=%s)', user_id)
            finally:
                close_old_connections()

        threading.Thread(target=_runner, daemon=True).start()

    transaction.on_commit(_send_after_commit)

    if request is not None:
        from django.contrib import messages as dj_messages

        dj_messages.success(
            request,
            'Cuenta creada. Estamos procesando tu correo de verificación; cuando llegue '
            '(revisá también spam), usá el enlace para poder iniciar sesión. '
            'Si no llega o el envío está al límite, podés solicitar otro desde el inicio de sesión.',
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
