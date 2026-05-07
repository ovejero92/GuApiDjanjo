from django.db import migrations


def seed_medios_de_pago_forwards(apps, schema_editor):
    MedioDePago = apps.get_model('myapp', 'MedioDePago')
    # Deben coincidir con Turno.MEDIO_DE_PAGO_CHOICES (slug → valor guardado en el turno).
    datos = (
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
    )
    for slug, nombre_visible in datos:
        MedioDePago.objects.get_or_create(
            slug=slug,
            defaults={'nombre_visible': nombre_visible},
        )


def seed_medios_de_pago_reverse(apps, schema_editor):
    MedioDePago = apps.get_model('myapp', 'MedioDePago')
    MedioDePago.objects.filter(
        slug__in=('efectivo', 'transferencia', 'tarjeta_debito', 'tarjeta_credito')
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0026_seed_planes_iniciales'),
    ]

    operations = [
        migrations.RunPython(seed_medios_de_pago_forwards, seed_medios_de_pago_reverse),
    ]
