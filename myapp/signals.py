from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Plan, Suscripcion

@receiver(post_save, sender=User)
def crear_suscripcion_gratuita(sender, instance, created, **kwargs):
    if created:
        try:
            plan_gratuito = Plan.objects.get(slug='free')
            Suscripcion.objects.create(usuario=instance, plan=plan_gratuito, is_active=True)
        except Plan.DoesNotExist:
            # Esto es importante: si el plan 'free' no existe, no hacemos nada para no romper el registro.
            # Lo crearemos manualmente desde el admin.
            pass