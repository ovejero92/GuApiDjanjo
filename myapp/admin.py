from django.contrib import admin
from django.contrib import messages as dj_messages
from django.core.exceptions import ObjectDoesNotExist
from .models import (
    Servicio,
    Profesional,
    SubServicio,
    Turno,
    HorarioLaboral,
    DiaNoDisponible,
    Reseña,
    Plan,
    Suscripcion,
    MedioDePago,
    Categoria,
    PerfilUsuario,
    EmailVerificationToken,
    EmailFailureLog,
)

admin.site.register(MedioDePago)
admin.site.register(Categoria)
admin.site.register(PerfilUsuario)
admin.site.register(HorarioLaboral)
admin.site.register(DiaNoDisponible)
admin.site.register(SubServicio)

admin.site.register(EmailVerificationToken)


@admin.register(EmailFailureLog)
class EmailFailureLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'recipient', 'subject', 'resolved', 'retry_count')
    list_filter = ('event_type', 'resolved', 'created_at')
    search_fields = ('recipient', 'subject', 'error_message')
    readonly_fields = ('created_at', 'event_type', 'recipient', 'subject', 'html_content', 'error_message', 'retry_count')


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
    extra = 1

class DiaNoDisponibleInline(admin.TabularInline):
    model = DiaNoDisponible
    extra = 1
    fields = ('fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin', 'motivo')

@admin.register(Profesional)
class ProfesionalAdmin(admin.ModelAdmin):
    inlines = [HorarioLaboralInline, DiaNoDisponibleInline]
    list_display = ('nombre', 'servicio', 'activo')
    list_filter = ('servicio',)
    search_fields = ('nombre', 'email')

def _servicio_plan_del_propietario_text(obj):
    if obj is None or not getattr(obj, 'pk', None):
        return '—'
    owner = getattr(obj, 'propietario', None)
    if owner is None:
        return '—'
    try:
        s = owner.suscripcion
    except ObjectDoesNotExist:
        return 'Sin suscripción'
    if not getattr(s, 'plan', None):
        return 'Sin plan asignado'
    activa_mp = 'sí' if s.is_active else 'no'
    return f'{s.plan.get_nombre_display()} · pago marcado activo: {activa_mp}'


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = (
        'nombre',
        'propietario',
        'plan_propietario',
        'esta_activo',
        'permite_multiples_profesionales',
    )
    readonly_fields = (
        'permite_multiples_profesionales',
        'plan_propietario',
        'plan_donde_esta_gestionado',
    )
    list_filter = ('esta_activo',)
    search_fields = ('nombre', 'propietario__username')
    actions = [activar_servicios, desactivar_servicios]
    prepopulated_fields = {'slug': ('nombre',)}

    @admin.display(description='Plan (propietario)')
    def plan_propietario(self, obj):
        return _servicio_plan_del_propietario_text(obj)

    @admin.display(description='Dónde gestionar el plan')
    def plan_donde_esta_gestionado(self, obj):
        return (
            'El Plan no es un campo de Servicio. Cada propietario tiene una fila en «Suscripción» '
            '(un Plan + is_active + mp_subscription_id). Para pruebas, editá la Suscripción de ese mismo '
            'usuario ahí mismo; para cobro real usar la página Precios.'
        )


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

@admin.action(description='[QA] Dar plan Profesional + pagos «activos» (sin Mercado Pago)')
def qa_forzar_plan_pro_activo(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            'Esta acción sólo puede usarla un superusuario.',
            level=dj_messages.ERROR,
        )
        return
    pro = Plan.objects.filter(slug='pro').first()
    if not pro:
        modeladmin.message_user(
            request,
            'No existe un Plan con slug «pro». Revisá la migración seed de planes.',
            level=dj_messages.ERROR,
        )
        return
    n = 0
    for sub in queryset:
        sub.plan = pro
        sub.is_active = True
        sub.save(update_fields=['plan', 'is_active'])
        n += 1
    modeladmin.message_user(
        request,
        f'Listo: {n} suscripción(es) pasadas a Plan Profesional con is_active=True (pruebas locales). '
        'Esto NO crea cobro real en Mercado Pago.',
    )


@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'plan', 'is_active', 'fecha_fin', 'servicios_propios_usuario')
    list_filter = ('plan', 'is_active')
    search_fields = ('usuario__username', 'usuario__email')
    readonly_fields = ('usuario',)
    list_select_related = ('usuario', 'plan')
    actions = [qa_forzar_plan_pro_activo]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        fld = form.base_fields.get('is_active')
        if fld is not None:
            fld.help_text = (
                'Plan Gratis se guarda como activo automáticamente. '
                'Para Profesional/Prime, marcá sí para dar acceso desde el panel (pruebas) '
                'o dejalo en no hasta que Mercado Pago confirme el cobro.'
            )
        return form

    @admin.display(description='Servicios del usuario')
    def servicios_propios_usuario(self, obj):
        return obj.usuario.servicios_propios.count()