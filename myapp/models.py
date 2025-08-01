import os
import sys
from io import BytesIO
from PIL import Image
from django.utils.text import slugify
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models.signals import post_save
from django.dispatch import receiver

def validar_tamaño_maximo_img(value):
    limite = 2 * 1024 * 1024
    if value.size > limite:
        raise ValidationError('¡El archivo es demasiado grande! El tamaño máximo es de 2 MB.')

class MedioDePago(models.Model):
    # El identificador que guardaremos en la base de datos (ej: "efectivo")
    slug = models.SlugField(max_length=50, unique=True, help_text="Identificador único para el código, ej: 'efectivo'")
    # El nombre que verá el usuario (ej: "Efectivo")
    nombre_visible = models.CharField(max_length=100, help_text="El nombre que verá el usuario en el formulario")

    def __str__(self):
        return self.nombre_visible

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
    duracion_buffer_minutos = models.PositiveIntegerField(
        default=15, # Un default razonable de 15 minutos
        help_text="Minutos de 'colchón' que se añadirán después de cada turno para preparación."
    )
    color_slot = models.CharField(
        max_length=7, 
        default='#4A4A4A', 
        help_text="Color de fondo para los botones de horarios y servicios."
    )
    color_slot_seleccionado = models.CharField(
        max_length=7, 
        default='#28a745', 
        help_text="Color de fondo para los botones CUANDO están seleccionados."
    )
    favoritos = models.ManyToManyField(User, related_name='servicios_favoritos', blank=True)
    color_primario = models.CharField(max_length=7, default='#007bff', help_text="Color principal")
    color_fondo = models.CharField(max_length=7, default='#333333', help_text="Color de fondo")
    medios_de_pago_aceptados = models.ManyToManyField(
        MedioDePago,
        blank=True, # Un servicio puede no tener ninguno seleccionado al principio
        help_text="Selecciona los medios de pago que aceptas en tu negocio."
    )
    imagen_banner = models.ImageField(upload_to='banners/', null=True, blank=True, help_text="Banner (máx 2MB)", validators=[validar_tamaño_maximo_img])
    footer_personalizado = models.TextField(blank=True, help_text="Texto o HTML simple para el footer")
    configuracion_inicial_completa = models.BooleanField(default=False)
    esta_activo = models.BooleanField( default=True, help_text="Indica si el propietario tiene el pago al día y el servicio está habilitado.")
    FONT_CHOICES = [
        ('Roboto, sans-serif', 'Simple y Moderna (Roboto)'),
        ('Open Sans, sans-serif', 'Clara y Amigable (Open Sans)'),
        ('Lato, sans-serif', 'Elegante y Profesional (Lato)'),
        ('Playfair Display, serif', 'Clásica y Sofisticada (Playfair Display)'),
        ('Montserrat, sans-serif', 'Audaz y Geométrica (Montserrat)'),
    ]
    fuente_titulos = models.CharField(
        max_length=100, choices=FONT_CHOICES, default='Montserrat, sans-serif',
        help_text="Elige la fuente para los títulos principales."
    )
    fuente_cuerpo = models.CharField(
        max_length=100, choices=FONT_CHOICES, default='Roboto, sans-serif',
        help_text="Elige la fuente para el texto general."
    )
    color_texto = models.CharField(
        max_length=7, default='#FFFFFF',
        help_text="Color para el texto principal. Elige un color oscuro si usas un fondo claro."
    )
    slug = models.SlugField(
        max_length=120, 
        unique=True,      # Asegura que no haya dos negocios con la misma URL.
        blank=True,       # Permite que esté vacío temporalmente para los servicios ya existentes.
        null=True,
        help_text="Generado automáticamente a partir del nombre para la URL."
    )
    
    # --- Campos para el Footer Estructurado ---
    footer_direccion = models.CharField(max_length=255, blank=True, null=True, help_text="Ej: Av. Siempreviva 742, Springfield")
    footer_telefono = models.CharField(max_length=20, blank=True, null=True, help_text="Ej: +54 9 11 1234-5678")
    footer_email = models.EmailField(max_length=255, blank=True, null=True, help_text="El email de contacto de tu negocio.")
    footer_instagram_url = models.URLField(max_length=255, blank=True, null=True, help_text="Pega aquí la URL completa de tu perfil de Instagram.")
    footer_facebook_url = models.URLField(max_length=255, blank=True, null=True, help_text="Pega aquí la URL completa de tu página de Facebook.")
    footer_tiktok_url = models.URLField(max_length=255, blank=True, null=True, help_text="Pega aquí la URL completa de tu perfil de TikTok.")
    
    def save(self, *args, **kwargs):
        # Si el servicio no tiene un slug, lo creamos a partir del nombre.
        if not self.slug:
            self.slug = slugify(self.nombre)
        else:
            self.slug = slugify(self.slug)
        # ... (el resto de tu lógica del método save para borrar imágenes se queda igual)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.imagen_banner:
            self.imagen_banner.delete(save=False)
        super().delete(*args, **kwargs)
        
    def __str__(self):
        return self.nombre
    
    @property
    def tiene_apariencia_premium_activa(self):
        """
        Comprueba si el propietario tiene una suscripción activa
        que le permita usar la personalización de apariencia.
        """
        try:
            # Buscamos la suscripción del propietario de este servicio
            suscripcion = self.propietario.suscripcion
            # Devolvemos True SOLO SI la suscripción está activa Y el plan lo permite
            return suscripcion.is_active and suscripcion.plan.allow_customization
        except Suscripcion.DoesNotExist:
            # Si el usuario no tiene un objeto de suscripción, no tiene acceso.
            return False
        except AttributeError:
            # Si la suscripción no tiene un plan asignado, no tiene acceso.
            return False

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
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='horarios')
    
    lunes = models.BooleanField(default=False)
    martes = models.BooleanField(default=False)
    miercoles = models.BooleanField(default=False)
    jueves = models.BooleanField(default=False)
    viernes = models.BooleanField(default=False)
    sabado = models.BooleanField(default=False)
    domingo = models.BooleanField(default=False)
    
    horario_apertura = models.TimeField()
    horario_cierre = models.TimeField()
    
    tiene_descanso = models.BooleanField(default=False, help_text="Marcar si hay un descanso en medio de la jornada.")
    descanso_inicio = models.TimeField(null=True, blank=True)
    descanso_fin = models.TimeField(null=True, blank=True)
    
    activo = models.BooleanField(default=True, help_text="Desmarcar para desactivar esta regla temporalmente.")

    class Meta:
        ordering = ['id']
        
    def __str__(self):
        dias_activos = []
        if self.lunes: dias_activos.append('Lu')
        if self.martes: dias_activos.append('Ma')
        if self.miercoles: dias_activos.append('Mi')
        if self.jueves: dias_activos.append('Ju')
        if self.viernes: dias_activos.append('Vi')
        if self.sabado: dias_activos.append('Sa')
        if self.domingo: dias_activos.append('Do')
        return f"Regla para {', '.join(dias_activos)} de {self.horario_apertura.strftime('%H:%M')} a {self.horario_cierre.strftime('%H:%M')}"

    def clean(self):
        if self.tiene_descanso and (not self.descanso_inicio or not self.descanso_fin):
            raise ValidationError("Si se marca que tiene descanso, se deben especificar las horas de inicio y fin del mismo.")
        if self.tiene_descanso and self.descanso_inicio >= self.descanso_fin:
            raise ValidationError("La hora de inicio del descanso debe ser anterior a la hora de fin.")
        if self.tiene_descanso and not (self.horario_apertura <= self.descanso_inicio and self.descanso_fin <= self.horario_cierre):
            raise ValidationError("El descanso debe estar dentro del horario de apertura y cierre.")

class DiaNoDisponible(models.Model):
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE, related_name='dias_no_disponibles')
    fecha = models.DateField(help_text="Día completo que no estará disponible.")
    
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
    MEDIO_DE_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia / Alias / Mercado Pago'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('tarjeta_credito', 'Tarjeta de Crédito'),
    ]

    medio_de_pago = models.CharField(
        max_length=20,
        choices=MEDIO_DE_PAGO_CHOICES,
        default='efectivo', # Un valor por defecto seguro
        help_text="El medio de pago elegido por el cliente."
    )
    medio_de_pago_final = models.CharField(
        max_length=50,
        blank=True, # Puede estar vacío hasta que se finalice el turno.
        null=True,
        help_text="El medio de pago real con el que se cobró el turno."
    )
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

class Plan(models.Model):
    PLAN_CHOICES = (
        ('free', 'Gratis'),
        ('pro', 'Profesional'),
        ('prime', 'Prime'),
    )
    nombre = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    slug = models.SlugField(unique=True, help_text="Se usa en las URLs. Ej: 'pro'")
    precio_mensual = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    # IDs de suscripción de Mercado Pago (¡Importante!)
    mp_plan_id = models.CharField(max_length=100, blank=True, null=True, 
                                  help_text="El ID del Plan de Suscripción creado en Mercado Pago")

    # --- Límites de las Funcionalidades ---
    allow_customization = models.BooleanField(default=False, help_text="Permite personalizar colores y banner.")
    allow_metrics = models.BooleanField(default=False, help_text="Permite acceder al dashboard de métricas.")
    # Puedes añadir más aquí en el futuro

    def __str__(self):
        return self.get_nombre_display()

class Suscripcion(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="suscripcion")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, related_name="suscripciones")
    is_active = models.BooleanField(default=False)
    mp_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    
    ha_visto_animacion_premium = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.usuario.username} - {self.plan.nombre if self.plan else 'Sin Plan'}"
    
class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    telefono = models.CharField(max_length=25, blank=True, null=True, help_text="Número de teléfono de contacto")

    def __str__(self):
        return f'Perfil de {self.usuario.username}'



@receiver(post_save, sender=User)
def crear_o_actualizar_perfil_usuario(sender, instance, created, **kwargs):
    PerfilUsuario.objects.get_or_create(usuario=instance)