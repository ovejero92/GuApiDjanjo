from django.urls import path, include
from rest_framework import routers
from . import views
from .api import ServicioViewSet, TurnoViewSet

router = routers.DefaultRouter()
router.register(r'servicios', ServicioViewSet, basename='servicios')
router.register(r'turnos', TurnoViewSet, basename='turnos')

urlpatterns = [
    # Vistas del frontend
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('register/', views.register, name='register'),
    path('servicio/<int:servicio_id>/', views.servicio_detail, name='servicio_detail'),

    # Auth (usando las vistas genéricas de Django)
    path('accounts/', include('django.contrib.auth.urls')),  # login, logout, etc.

    # API REST
    path('api/', include(router.urls)),
]
