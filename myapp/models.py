import os
import sys
from io import BytesIO
from PIL import Image

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile

def validar_tamaño_maximo_img(value):
    limite = 2 * 1024 * 1024
    if value.size > limite:
        raise ValidationError('¡El archivo es demasiado grande! El tamaño máximo es de 2 MB.')

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, help_text="Versión amigable para URL, ej: peluquerias")
    
    class Meta:
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre

class Servicio(models.Model):
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servicios_propios')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='servicios')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(default="Sin descripción")
    direccion = models.CharField(max_length=200, default="Sin dirección")
    favoritos = models.ManyToManyField(User, related_name='servicios_favoritos', blank=True)
    color_primario = models.CharField(max_length=7, default='#007bff', help_text="Color principal")
    color_fondo = models.CharField(max_length=7, default='#333333', help_text="Color de fondo")
    imagen_banner = models.ImageField(upload_to='banners/', null=True, blank=True, help_text="Banner (máx 2MB)", validators=[validar_tamaño_maximo_img])
    footer_personalizado = models.TextField(blank=True, help_text="Texto o HTML simple para el footer")
    configuracion_inicial_completa = models.BooleanField(default=False)
    
    def __str__(self):
        return self.nombre

class SubServicio(models.Model):
    # Vinculado al negocio principal
    servicio_padre = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='sub_servicios')
    
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    duracion = models.PositiveIntegerField(help_text="Duración en minutos")
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.servicio_padre.nombre})"

class HorarioLaboral(models.Model):
    DIA_SEMANA_CHOICES = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.IntegerField(choices=DIA_SEMANA_CHOICES)
    horario_apertura = models.TimeField()
    horario_cierre = models.TimeField()
    activo = models.BooleanField(default=True, help_text="Marcar si el servicio está abierto este día")

    class Meta:
        unique_together = ('servicio', 'dia_semana') # Un servicio solo puede tener una configuración por día
        ordering = ['dia_semana']

    def __str__(self):
        return f"{self.servicio.nombre} - {self.get_dia_semana_display()}: {self.horario_apertura.strftime('%H:%M')} a {self.horario_cierre.strftime('%H:%M')}"

class DiaNoDisponible(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='dias_no_disponibles')
    fecha = models.DateField(help_text="Día completo que no estará disponible.")
    # Para bloqueos parciales (ej: una cita médica de 14:00 a 15:00)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    motivo = models.CharField(max_length=255, blank=True, help_text="Ej: Vacaciones, Feriado, Cita médica")

    def __str__(self):
        if self.hora_inicio and self.hora_fin:
            return f"Bloqueo en {self.servicio.nombre} el {self.fecha} de {self.hora_inicio.strftime('%H:%M')} a {self.hora_fin.strftime('%H:%M')}"
        return f"Día completo no disponible en {self.servicio.nombre}: {self.fecha}"

class Turno(models.Model):
    # Mantenemos la relación con el Servicio principal para facilitar las consultas y restricciones.
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='turnos')
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='turnos_solicitados')
    fecha = models.DateField()
    hora = models.TimeField()
    
    # ¡NUEVO CAMPO! La duración total calculada de todos los sub-servicios reservados.
    duracion_total = models.PositiveIntegerField(default=30, help_text="Duración total calculada en minutos")
    
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('confirmado', 'Confirmado'), ('cancelado', 'Cancelado'), ('completado', 'Completado')]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    
    # ¡MODIFICADO! Este campo ahora puede estar vacío, se rellenará al finalizar.
    ingreso_real = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    visto_por_cliente = models.BooleanField(default=False)
    
    # ¡NUEVO CAMPO! Relación "Muchos a Muchos" para los servicios que se solicitaron.
    sub_servicios_solicitados = models.ManyToManyField(SubServicio, blank=True)

    class Meta:
        # La restricción sigue funcionando como antes.
        unique_together = ('servicio', 'fecha', 'hora')

    def __str__(self):
        return f"Turno para {self.cliente.username} en {self.servicio.nombre} el {self.fecha} a las {self.hora}"

class Reseña(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='reseñas')
    turno = models.OneToOneField(Turno, on_delete=models.CASCADE, related_name='reseña')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reseñas_hechas')
    calificacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], help_text="Calificación de 1 a 5 estrellas")
    comentario = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('turno', 'usuario')
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Reseña de {self.usuario.username} para {self.servicio.nombre} ({self.calificacion} estrellas)"