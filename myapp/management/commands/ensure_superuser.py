import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/asegura un superusuario a partir de variables de entorno."

    def handle(self, *args, **options):
        """
        Variables soportadas:
          - DJANGO_SUPERUSER_USERNAME (opcional si hay email)
          - DJANGO_SUPERUSER_EMAIL (opcional si hay username)
          - DJANGO_SUPERUSER_PASSWORD (requerida para crear)
          - DJANGO_SUPERUSER_CREATE=1 (si no está en 1/true/yes, no hace nada)
        """
        flag = (os.getenv("DJANGO_SUPERUSER_CREATE") or "").strip().lower()
        if flag not in {"1", "true", "yes", "y"}:
            self.stdout.write("DJANGO_SUPERUSER_CREATE no habilitado. Saltando.")
            return

        username = (os.getenv("DJANGO_SUPERUSER_USERNAME") or "").strip()
        email = (os.getenv("DJANGO_SUPERUSER_EMAIL") or "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD") or ""

        if not password:
            self.stderr.write("Falta DJANGO_SUPERUSER_PASSWORD. No se puede crear el superusuario.")
            return

        User = get_user_model()

        lookup = {}
        if email:
            lookup["email"] = email
        elif username:
            lookup[User.USERNAME_FIELD] = username
        else:
            self.stderr.write("Falta DJANGO_SUPERUSER_EMAIL o DJANGO_SUPERUSER_USERNAME.")
            return

        user = User.objects.filter(**lookup).first()
        if user:
            changed = False
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if changed:
                user.save(update_fields=["is_superuser", "is_staff"])
                self.stdout.write(self.style.SUCCESS("Superusuario existente actualizado (staff/superuser)."))
            else:
                self.stdout.write(self.style.SUCCESS("Superusuario ya existe."))
            return

        create_kwargs = {}
        # Set required fields
        if email:
            create_kwargs["email"] = email
        if User.USERNAME_FIELD != "email":
            # If the model uses username (default), require it; fall back to email prefix.
            if not username:
                username = (email.split("@", 1)[0] if email else "admin")
            create_kwargs[User.USERNAME_FIELD] = username

        user = User.objects.create_superuser(password=password, **create_kwargs)
        self.stdout.write(self.style.SUCCESS(f"Superusuario creado: {getattr(user, User.USERNAME_FIELD, '')}"))

