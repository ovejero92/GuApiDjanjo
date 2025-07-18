# myapp/middleware.py
from django.shortcuts import redirect
from django.urls import reverse

# class OnboardingMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         # Solo aplicamos la lógica si el usuario está logueado y no es superusuario
#         if request.user.is_authenticated and not request.user.is_superuser:
#             # Si el usuario es un propietario (tiene servicios asignados)
#             if hasattr(request.user, 'servicios_propios') and request.user.servicios_propios.exists():
#                 servicio = request.user.servicios_propios.first()
#                 # Si no ha completado el onboarding y no está ya en la página de onboarding...
#                 if not servicio.configuracion_inicial_completa and request.path != reverse('onboarding'):
#                     # ...y si la URL a la que intenta acceder está dentro del dashboard...
#                     if request.path.startswith('/dashboard/'):
#                         return redirect('onboarding')

#         response = self.get_response(request)
#         return response