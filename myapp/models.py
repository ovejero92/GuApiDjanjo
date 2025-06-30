from django.db import models
from django.contrib.auth.models import User
from datetime import time

class Servicio(models.Model):
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
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora = models.TimeField()

    def __str__(self):
        return f"{self.usuario.username} - {self.servicio.nombre} - {self.fecha} {self.hora}"

    class Meta:
        unique_together = ('servicio', 'fecha', 'hora')  # No se pueden superponer turnos
