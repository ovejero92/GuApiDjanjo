# Generated by Django 5.2.3 on 2025-07-06 21:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0011_remove_servicio_horario_apertura_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiaNoDisponible',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(help_text='Día completo que no estará disponible.')),
                ('hora_inicio', models.TimeField(blank=True, null=True)),
                ('hora_fin', models.TimeField(blank=True, null=True)),
                ('motivo', models.CharField(blank=True, help_text='Ej: Vacaciones, Feriado, Cita médica', max_length=255)),
                ('servicio', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dias_no_disponibles', to='myapp.servicio')),
            ],
        ),
    ]
