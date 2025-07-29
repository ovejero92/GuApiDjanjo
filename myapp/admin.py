from django.contrib import admin
from .models import Servicio, SubServicio, Turno, HorarioLaboral, DiaNoDisponible, Reseña,Plan,Suscripcion, MedioDePago

admin.site.register(MedioDePago)

@admin.action(description="Desactivar servicios seleccionados (pago vencido)")
def desactivar_servicios(modeladmin, request, queryset):
    queryset.update(esta_activo=False)

@admin.action(description="Activar servicios seleccionados (pago recibido)")
def activar_servicios(modeladmin, request, queryset):
    queryset.update(esta_activo=True)

class SubServicioInline(admin.TabularInline):
    model = SubServicio
    extra = 1
    fields = ('nombre', 'descripcion', 'duracion', 'precio')

class HorarioLaboralInline(admin.TabularInline):
    model = HorarioLaboral
    extra = 1
    max_num = 7
    fields = ('dia_semana', 'activo', 'horario_apertura', 'horario_cierre')

class DiaNoDisponibleInline(admin.TabularInline):
    model = DiaNoDisponible
    extra = 1
    fields = ('fecha', 'hora_inicio', 'hora_fin', 'motivo')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'propietario', 'esta_activo')
    list_filter = ('esta_activo',)
    search_fields = ('nombre', 'propietario__username')
    actions = [activar_servicios, desactivar_servicios]
    
    inlines = [
        SubServicioInline,
        HorarioLaboralInline,
        DiaNoDisponibleInline,
    ]

@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('id', 'servicio', 'cliente', 'fecha', 'hora', 'estado')
    list_filter = ('estado', 'fecha', 'servicio')
    search_fields = ('cliente__username', 'servicio__nombre')

@admin.register(Reseña)
class ReseñaAdmin(admin.ModelAdmin):
    list_display = ('turno', 'usuario', 'calificacion', 'fecha_creacion')
    list_filter = ('calificacion',)

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """Configuración para el modelo Plan en el panel de admin."""
    list_display = ('get_nombre_display', 'slug', 'precio_mensual', 'mp_plan_id')
    # Esta línea es "magia": autocompleta el campo 'slug' mientras escribes el nombre.
    prepopulated_fields = {'slug': ('nombre',)}

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    """Configuración para el modelo Suscripcion en el panel de admin."""
    list_display = ('usuario', 'plan', 'is_active', 'fecha_fin')
    list_filter = ('plan', 'is_active')
    search_fields = ('usuario__username', 'usuario__email')
    # Hacemos que el campo de usuario sea de solo lectura para no cambiarlo por error.
    readonly_fields = ('usuario',)