from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import time

class Servicio(models.Model):
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servicios_propios')
    
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(default="Sin descripción")
    direccion = models.CharField(max_length=200, default="Sin dirección")
    precio_estandar = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    horario_apertura = models.TimeField(default=time(9, 0))
    horario_cierre = models.TimeField(default=time(18, 0))

    def __str__(self):
        return self.nombre

class Turno(models.Model):
    
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='turnos_solicitados') # 'related_name' evita conflictos
    fecha = models.DateField()
    hora = models.TimeField()
    visto_por_cliente = models.BooleanField(default=False)
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
        ('completado', 'Completado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')

    def __str__(self):
        return f"{self.cliente.username} - {self.servicio.nombre} - {self.fecha} {self.hora}"

    class Meta:
        unique_together = ('servicio', 'fecha', 'hora')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)