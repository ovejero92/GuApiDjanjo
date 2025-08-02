from django.urls import path, include
from rest_framework import routers
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views 
from . import views
from .api import ServicioViewSet, TurnoViewSet

router = routers.DefaultRouter()
router.register(r'servicios', ServicioViewSet, basename='servicios')
router.register(r'turnos', TurnoViewSet, basename='turnos')

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('s/<slug:servicio_slug>/', views.servicio_detail, name='servicio_detail'),
    path('api/reseñas/<slug:servicio_slug>/', views.api_get_reseñas, name='api_get_reseñas'),
    path('dashboard/', views.dashboard_turnos, name='dashboard_propietario'),
    path('dashboard/turnos/', views.dashboard_turnos, name='dashboard_turnos'),
    path('dashboard/horarios/', views.dashboard_horarios, name='dashboard_horarios'),
    path('dashboard/metricas/', views.dashboard_metricas, name='dashboard_metricas'),
    path('dashboard/servicios/', views.dashboard_servicios, name='dashboard_servicios'),
    path('turno/reseña/crear/<int:turno_id>/', views.crear_reseña, name='crear_reseña'),
    path('mis-turnos/', views.mis_turnos, name='mis_turnos'),
    path('mis-favoritos/', views.mis_favoritos, name='mis_favoritos'), 
    path("googleef49e9e659c3e137.html", TemplateView.as_view(
        template_name="googleef49e9e659c3e137.html",
        content_type="text/html"
    )),
    path('api/notificaciones-propietario/', views.obtener_notificaciones_propietario, name='obtener_notificaciones_propietario'),
    path('servicio/toggle-favorito/<int:servicio_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('activate/<slug:uidb64>/<slug:token>/', views.activate, name='activate'),
    path('dashboard/catalogo/', views.dashboard_catalogo, name='dashboard_catalogo'),
    path('terminos-y-condiciones/', views.terminos_y_condiciones, name='terminos'),
    path('empezar/', views.crear_servicio_paso1, name='crear_servicio_paso1'),
    path('crear-servicio/', views.crear_servicio_paso2, name='crear_servicio_paso2'),
    path('politica-de-privacidad/', views.politica_de_privacidad, name='privacidad'),
    path('onboarding/marcar-completo/', views.marcar_onboarding_completo, name='marcar_onboarding_completo'),
    path('dashboard/detalles/', views.dashboard_detalles_negocio, name='dashboard_detalles_negocio'),
    path('dashboard/calendario/', views.dashboard_calendario, name='dashboard_calendario'),
    path('api/turnos-por-dia/', views.api_turnos_por_dia, name='api_turnos_por_dia'),
    path('turno/confirmar/<int:turno_id>/', views.confirmar_turno, name='confirmar_turno'),
    path('turno/cancelar/<int:turno_id>/', views.cancelar_turno, name='cancelar_turno'),
    path('turno/finalizar/<int:turno_id>/', views.finalizar_turno, name='finalizar_turno'),
    path('precios/', views.precios, name='precios'),
    path('crear-suscripcion/<slug:plan_slug>/', views.crear_suscripcion_mp, name='crear_suscripcion'),
    path('pago-exitoso/', views.pago_exitoso, name='pago_exitoso'),
    path('webhooks/mp/', views.webhook_mp, name='webhook_mp'),
    path('editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('api/', include(router.urls)),
    path('api/notificaciones/', views.obtener_notificaciones, name='obtener_notificaciones'),
    path('api/slots-disponibles/<int:servicio_id>/', views.obtener_slots_disponibles, name='obtener_slots_disponibles'),
]