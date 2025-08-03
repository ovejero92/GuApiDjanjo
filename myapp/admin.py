from django.contrib import admin
from .models import Servicio, SubServicio, Turno, HorarioLaboral, DiaNoDisponible, Reseña, Plan, Suscripcion, MedioDePago, Categoria, PerfilUsuario

admin.site.register(MedioDePago)
admin.site.register(Categoria)
admin.site.register(PerfilUsuario)
admin.site.register(HorarioLaboral)
admin.site.register(DiaNoDisponible)
admin.site.register(SubServicio)


@admin.action(description="Activar servicios seleccionados (pago recibido)")
def activar_servicios(modeladmin, request, queryset):
    queryset.update(esta_activo=True)

@admin.action(description="Desactivar servicios seleccionados (pago vencido)")
def desactivar_servicios(modeladmin, request, queryset):
    queryset.update(esta_activo=False)



class SubServicioInline(admin.TabularInline):
    model = SubServicio
    extra = 1
    fields = ('nombre', 'descripcion', 'duracion', 'precio')

class HorarioLaboralInline(admin.TabularInline):
    model = HorarioLaboral
    fields = (
        ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'),
        ('horario_apertura', 'horario_cierre'),
        ('tiene_descanso', 'descanso_inicio', 'descanso_fin'),
        'activo'
    )
    extra = 0

class DiaNoDisponibleInline(admin.TabularInline):
    model = DiaNoDisponible
    extra = 1
    fields = ('fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin', 'motivo')


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'propietario', 'esta_activo')
    list_filter = ('esta_activo',)
    search_fields = ('nombre', 'propietario__username')
    actions = [activar_servicios, desactivar_servicios]
    prepopulated_fields = {'slug': ('nombre',)}
    
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
    list_display = ('get_nombre_display', 'slug', 'precio_mensual', 'mp_plan_id')
    prepopulated_fields = {'slug': ('nombre',)}

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plan', 'is_active', 'fecha_fin')
    list_filter = ('plan', 'is_active')
    search_fields = ('usuario__username', 'usuario__email')
    readonly_fields = ('usuario',)