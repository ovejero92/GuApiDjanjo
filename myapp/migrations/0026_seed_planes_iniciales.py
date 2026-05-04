from decimal import Decimal

from django.db import migrations


def seed_planes_forwards(apps, schema_editor):
    Plan = apps.get_model('myapp', 'Plan')
    espec = (
        {
            'nombre': 'free',
            'slug': 'free',
            'precio_mensual': Decimal('0'),
            'allow_customization': False,
            'allow_metrics': False,
            'mp_plan_id': None,
        },
        {
            'nombre': 'pro',
            'slug': 'pro',
            'precio_mensual': Decimal('2999'),
            'allow_customization': True,
            'allow_metrics': True,
            'mp_plan_id': None,
        },
        {
            'nombre': 'prime',
            'slug': 'prime',
            'precio_mensual': Decimal('4999'),
            'allow_customization': True,
            'allow_metrics': True,
            'mp_plan_id': None,
        },
    )
    for row in espec:
        slug = row['slug']
        Plan.objects.update_or_create(slug=slug, defaults=row)


def seed_planes_reverse(apps, schema_editor):
    Plan = apps.get_model('myapp', 'Plan')
    Plan.objects.filter(slug__in=('free', 'pro', 'prime')).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0025_alter_turno_medio_de_pago'),
    ]

    operations = [
        migrations.RunPython(seed_planes_forwards, seed_planes_reverse),
    ]
