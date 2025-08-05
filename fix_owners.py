import os
import django

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings') # Reemplaza 'GuApiDjanjo.settings' con el nombre de tu archivo de settings
django.setup()

from myapp.models import Servicio, Profesional, HorarioLaboral, User # Reemplaza 'myapp' con el nombre de tu app

def fix_service_owners():
    print("Iniciando revisión de servicios...")
    all_services = Servicio.objects.all()

    for service in all_services:
        owner = service.propietario
        # Verificamos si ya existe un perfil de Profesional para el dueño de ESTE servicio
        has_owner_profile = Profesional.objects.filter(servicio=service, user_account=owner).exists()

        if not has_owner_profile:
            print(f"Arreglando servicio '{service.nombre}' (ID: {service.id})...")
            
            # 1. Creamos el perfil de Profesional para el propietario
            profesional_propietario = Profesional.objects.create(
                servicio=service,
                nombre=owner.first_name or owner.username,
                email=owner.email,
                user_account=owner,
                activo=True # Lo activamos por defecto
            )
            print(f" -> Perfil de Profesional creado para el dueño '{owner.username}'.")

            # 2. Le creamos un horario por defecto para que pueda recibir turnos
            HorarioLaboral.objects.create(
                profesional=profesional_propietario,
                activo=True,
                lunes=True, martes=True, miercoles=True, jueves=True, viernes=True,
                horario_apertura='09:00:00',
                horario_cierre='18:00:00'
            )
            print(" -> Horario por defecto (L-V 9-18) asignado.")
        else:
            print(f"Servicio '{service.nombre}' (ID: {service.id}) ya está correcto.")
    
    print("\n¡Revisión completada!")

if __name__ == "__main__":
    fix_service_owners()