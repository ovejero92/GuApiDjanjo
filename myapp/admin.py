from django.contrib import admin
from .models import Servicio, SubServicio, Turno, HorarioLaboral, DiaNoDisponible, Reseña

@admin.action(description="Desactivar servicios seleccionados (pago vencido)")
def desactivar_servicios(modeladmin, request, queryset):
    """
    Acción que marca los servicios seleccionados como inactivos.
    """
    queryset.update(esta_activo=False)

@admin.action(description="Activar servicios seleccionados (pago recibido)")
def activar_servicios(modeladmin, request, queryset):
    """
    Acción que marca los servicios seleccionados como activos.
    """
    queryset.update(esta_activo=True)

class SubServicioInline(admin.TabularInline):
    """Permite editar los SubServicios directamente desde la página de Servicio."""
    model = SubServicio
    extra = 1 # Siempre mostrar un campo vacío para añadir uno nuevo.
    fields = ('nombre', 'descripcion', 'duracion', 'precio')

class HorarioLaboralInline(admin.TabularInline):
    """Permite editar los Horarios directamente desde la página de Servicio."""
    model = HorarioLaboral
    extra = 1 # Permitir añadir días si faltan.
    max_num = 7 # No permitir más de 7 días.
    fields = ('dia_semana', 'activo', 'horario_apertura', 'horario_cierre')

class DiaNoDisponibleInline(admin.TabularInline):
    """Permite añadir bloqueos directamente desde la página de Servicio."""
    model = DiaNoDisponible
    extra = 1
    fields = ('fecha', 'hora_inicio', 'hora_fin', 'motivo')

# --- Clase principal para el Admin de Servicio ---

@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    """Configuración avanzada para el modelo Servicio en el panel de admin."""
    list_display = ('nombre', 'propietario', 'esta_activo')
    list_filter = ('esta_activo',)
    search_fields = ('nombre', 'propietario__username')
    # Añadimos los modelos relacionados para gestionarlos todos desde un solo lugar.
    actions = [activar_servicios, desactivar_servicios]
    
    inlines = [
        SubServicioInline,
        HorarioLaboralInline,
        DiaNoDisponibleInline,
    ]

# --- Registros de otros modelos (si quieres verlos por separado) ---

@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('id', 'servicio', 'cliente', 'fecha', 'hora', 'estado')
    list_filter = ('estado', 'fecha', 'servicio')
    search_fields = ('cliente__username', 'servicio__nombre')

@admin.register(Reseña)
class ReseñaAdmin(admin.ModelAdmin):
    list_display = ('turno', 'usuario', 'calificacion', 'fecha_creacion')
    list_filter = ('calificacion',)

