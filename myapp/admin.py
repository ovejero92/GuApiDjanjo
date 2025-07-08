from django.contrib import admin
from .models import Servicio, Turno, HorarioLaboral, DiaNoDisponible

# ========== NUEVA CLASE INLINE ==========
class HorarioLaboralInline(admin.TabularInline):
    model = HorarioLaboral
    extra = 7 # Muestra 7 slots para rellenar, uno por cada día de la semana
    max_num = 7 # No permite crear más de 7

class DiaNoDisponibleInline(admin.TabularInline):
    model = DiaNoDisponible
    extra = 1

# ========== CLASE ADMIN MODIFICADA ==========
class ServicioAdmin(admin.ModelAdmin):
    inlines = [HorarioLaboralInline, DiaNoDisponibleInline]

# Desregistra el modelo Servicio si ya estaba registrado de forma simple
try:
    admin.site.unregister(Servicio)
except admin.sites.NotRegistered:
    pass

# Registra Servicio con la nueva configuración y registra Turno
admin.site.register(Servicio, ServicioAdmin)
admin.site.register(Turno)
# No necesitamos registrar HorarioLaboral por separado, ya se gestiona desde Servicio.