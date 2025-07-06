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
    path('register/', views.register, name='register'),
    path('servicio/<int:servicio_id>/', views.servicio_detail, name='servicio_detail'),

    # Dashboards
    path('dashboard/', views.dashboard_propietario, name='dashboard_propietario'),
    path('mis-turnos/', views.mis_turnos, name='mis_turnos'),

    # ========== INICIO DE LA MODIFICACIÓN ==========
    # AUTENTICACIÓN: Usamos nuestra CustomLoginView para el login
    path('accounts/login/', views.CustomLoginView.as_view(), name='login'),
    
    # Para el logout, usamos la vista de Django pero le decimos explícitamente a dónde ir.
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='index'), name='logout'),
    # ========== FIN DE LA MODIFICACIÓN ==========
    
     # ========== INICIO DE LA MODIFICACIÓN: URLs para gestionar turnos ==========
    path('turno/confirmar/<int:turno_id>/', views.confirmar_turno, name='confirmar_turno'),
    path('turno/cancelar/<int:turno_id>/', views.cancelar_turno, name='cancelar_turno'),
    # ========== FIN DE LA MODIFICACIÓN ==========
    
    # ========== INICIO DE LA MODIFICACIÓN: URL para editar perfil ==========
    path('editar-perfil/', views.editar_perfil, name='editar_perfil'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        success_url='/accounts/password_change/done/' # A dónde ir tras el éxito
    ), name='password_change'),
    
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    # ========== FIN DE LA MODIFICACIÓN ==========
    
    # API REST
    path('api/', include(router.urls)),
    
    # ========== INICIO DE LA MODIFICACIÓN ==========
    path('api/notificaciones/', views.obtener_notificaciones, name='obtener_notificaciones'),
    # ========== FIN DE LA MODIFICACIÓN ==========
]