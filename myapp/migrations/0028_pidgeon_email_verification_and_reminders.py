# Generated manually for TurnosOk / Pidgeon email verification

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def set_existing_profiles_email_verified(apps, schema_editor):
    PerfilUsuario = apps.get_model('myapp', 'PerfilUsuario')
    PerfilUsuario.objects.all().update(email_verified=True)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('myapp', '0027_seed_medios_de_pago'),
    ]

    operations = [
        migrations.AddField(
            model_name='perfilusuario',
            name='email_verified',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(set_existing_profiles_email_verified, noop_reverse),
        migrations.AddField(
            model_name='turno',
            name='recordatorio_enviado',
            field=models.BooleanField(
                default=False,
                help_text='True si ya se enviaron los recordatorios ~15 min antes del turno.',
            ),
        ),
        migrations.AlterField(
            model_name='turno',
            name='estado',
            field=models.CharField(
                choices=[
                    ('pendiente', 'Pendiente'),
                    ('confirmado', 'Confirmado'),
                    ('rechazado', 'Rechazado'),
                    ('cancelado', 'Cancelado'),
                    ('completado', 'Completado'),
                ],
                default='pendiente',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='EmailVerificationToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                (
                    'user',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='email_verification_tokens',
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='EmailFailureLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(max_length=50)),
                ('recipient', models.EmailField(max_length=254)),
                ('subject', models.CharField(max_length=255)),
                ('html_content', models.TextField()),
                ('error_message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('retry_count', models.IntegerField(default=0)),
                ('resolved', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
