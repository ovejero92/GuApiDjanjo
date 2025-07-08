from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Servicio(models.Model):
    propietario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servicios_propios')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(default="Sin descripción")
    direccion = models.CharField(max_length=200, default="Sin dirección")
    precio_estandar = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    duracion = models.PositiveIntegerField(default=30, help_text="Duración del servicio en minutos")
    favoritos = models.ManyToManyField(User, related_name='servicios_favoritos', blank=True)
    
    def __str__(self):
        return self.nombre

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
    ingreso_real = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        help_text="Ingreso monetario real generado por este turno."
    )

    def __str__(self):
        return f"{self.cliente.username} - {self.servicio.nombre} - {self.fecha} {self.hora}"

    class Meta:
        unique_together = ('servicio', 'fecha', 'hora')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class Reseña(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='reseñas')
    # El turno nos sirve de "prueba" de que el usuario realmente usó el servicio.
    turno = models.OneToOneField(Turno, on_delete=models.CASCADE, related_name='reseña')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reseñas_hechas')
    calificacion = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación de 1 a 5 estrellas"
    )
    comentario = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('turno', 'usuario') # Un usuario solo puede dejar una reseña por turno.
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Reseña de {self.usuario.username} para {self.servicio.nombre} ({self.calificacion} estrellas)"