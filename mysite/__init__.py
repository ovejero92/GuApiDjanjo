# mysite/__init__.py

def create_default_superuser():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    if not User.objects.filter(username='adminrender').exists():
        print("🛠 Creando superusuario...")
        User.objects.create_superuser(
            username='ovejero92',
            email='ovejero.gustavo92@render.com',
            password='Cyg190921'
        )
        print("✅ Superusuario creado: adminrender / admin1234")

# Ejecutar después de iniciar Django
from django.core.management import signals
def create_admin_after_start(*args, **kwargs):
    from django.db import connection
    if connection.vendor != 'sqlite':  # Solo en producción (Render)
        create_default_superuser()

signals.post_migrate.connect(create_admin_after_start)
