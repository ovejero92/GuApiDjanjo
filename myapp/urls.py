from django.urls import path, include
from rest_framework import routers
from django.contrib.auth import views as auth_views 
from . import views
from .api import ServicioViewSet, TurnoViewSet

router = routers.DefaultRouter()
router.register(r'servicios', ServicioViewSet, basename='servicios')
router.register(r'turnos', TurnoViewSet, basename='turnos')

urlpatterns = [
    # Vistas principales
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('servicio/<int:servicio_id>/', views.servicio_detail, name='servicio_detail'),

    # Dashboards
    path('dashboard/', views.dashboard_turnos, name='dashboard_propietario'),
     # URLs específicas para cada sección del dashboard
    path('dashboard/turnos/', views.dashboard_turnos, name='dashboard_turnos'),
    path('dashboard/horarios/', views.dashboard_horarios, name='dashboard_horarios'),
    path('dashboard/metricas/', views.dashboard_metricas, name='dashboard_metricas'),
    path('dashboard/servicios/', views.dashboard_servicios, name='dashboard_servicios'),
    path('turno/reseña/crear/<int:turno_id>/', views.crear_reseña, name='crear_reseña'),
    path('mis-turnos/', views.mis_turnos, name='mis_turnos'),
    path('mis-favoritos/', views.mis_favoritos, name='mis_favoritos'),
    path('servicio/toggle-favorito/<int:servicio_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('activate/<slug:uidb64>/<slug:token>/', views.activate, name='activate'),
    path('dashboard/catalogo/', views.dashboard_catalogo, name='dashboard_catalogo'),
    
     # ========== INICIO DE LA MODIFICACIÓN: URLs para gestionar turnos ==========
    path('turno/confirmar/<int:turno_id>/', views.confirmar_turno, name='confirmar_turno'),
    path('turno/cancelar/<int:turno_id>/', views.cancelar_turno, name='cancelar_turno'),
    path('turno/finalizar/<int:turno_id>/', views.finalizar_turno, name='finalizar_turno'),
    # ========== FIN DE LA MODIFICACIÓN ==========
    
    # ========== INICIO DE LA MODIFICACIÓN: URL para editar perfil ==========
    path('editar-perfil/', views.editar_perfil, name='editar_perfil'),
    # ========== FIN DE LA MODIFICACIÓN ==========
    
    # API REST
    path('api/', include(router.urls)),
    # ========== INICIO DE LA MODIFICACIÓN ==========
    path('api/notificaciones/', views.obtener_notificaciones, name='obtener_notificaciones'),
    # ========== FIN DE LA MODIFICACIÓN ==========
    # ========== INICIO DE LA MODIFICACIÓN: API para slots de tiempo ==========
    path('api/slots-disponibles/<int:servicio_id>/', views.obtener_slots_disponibles, name='obtener_slots_disponibles'),
    # ========== FIN DE LA MODIFICACIÓN ==========
]