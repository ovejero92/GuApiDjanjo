from django.urls import path, include
from rest_framework import routers
from . import views
from .api import ProjectViewSet

# Creamos el router de DRF
router = routers.DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='projects')

urlpatterns = [
    # Tus vistas tradicionales
    path('', views.index, name="index"),
    path('about/', views.about, name="about"),
    path('hello/<str:username>/', views.hello),
    path('projects/', views.projects, name="projects"),
    path('projects/<int:id>/', views.project_detail, name="project_detail"),
    path('tasks/', views.tasks, name="tasks"),
    path('create_task/', views.create_task, name="create_task"),
    path('create_project/', views.create_project, name="create_project"),

    # Vistas REST
    path('api/', include(router.urls)),
]
