from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages, auth
from .models import Servicio, Turno
from .forms import CustomUserCreationForm, TurnoForm, UserUpdateForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.http import JsonResponse

# ========== INICIO DE LA MODIFICACIÓN ==========
# Importaciones necesarias para la nueva vista de Login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
# ========== FIN DE LA MODIFICACIÓN ==========


def index(request):
    servicios = Servicio.objects.all()
    return render(request, 'index.html', {'servicios': servicios})

def about(request):
    return render(request, 'about.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def servicio_detail(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        form = TurnoForm(request.POST, servicio=servicio)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.cliente = request.user
            try:
                turno.save()
                return redirect('index')
            except ValidationError as e:
                # Agregar error al formulario para mostrarlo en la plantilla
                form.add_error(None, 'Ya existe un turno para ese servicio, fecha y hora.')
    else:
        form = TurnoForm(servicio=servicio)
    
    # --- LÓGICA PARA MOSTRAR HORARIOS OCUPADOS ---
    # Obtenemos los turnos de hoy para empezar
    hoy = timezone.localdate()
    turnos_del_dia = Turno.objects.filter(
        servicio=servicio, 
        fecha=hoy, 
        estado__in=['pendiente', 'confirmado'] # Solo contamos los que ocupan un lugar
    )
    horas_ocupadas = [t.hora.strftime("%H:%M") for t in turnos_del_dia]

    return render(request, 'servicio_detail.html', {
        'servicio': servicio,
        'form': form,
        'horas_ocupadas': horas_ocupadas, # Pasamos la lista a la plantilla
        'fecha_mostrada': hoy,
    })
    
@login_required
def dashboard_propietario(request):
    # Buscamos los servicios que pertenecen al usuario logueado
    servicios_del_propietario = Servicio.objects.filter(propietario=request.user)
    
    # Obtenemos todos los turnos de todos sus servicios
    turnos = Turno.objects.filter(servicio__in=servicios_del_propietario).order_by('fecha', 'hora')

    # Filtramos turnos para mostrar_
    hoy = timezone.localdate()
    turnos_pendientes = turnos.filter(fecha__gte=hoy, estado='pendiente').order_by('fecha', 'hora')
    turnos_confirmados = turnos.filter(fecha__gte=hoy, estado='confirmado').order_by('fecha', 'hora')
    turnos_pasados = turnos.filter(fecha__lt=hoy).order_by('-fecha', '-hora')

    context = {
        'servicios': servicios_del_propietario,
        'turnos_pendientes': turnos_pendientes,
        'turnos_confirmados': turnos_confirmados,
        'turnos_pasados': turnos_pasados
    }
    return render(request, 'dashboard_propietario.html', context)

@login_required
def mis_turnos(request):
    turnos = request.user.turnos_solicitados.order_by('fecha', 'hora')
    
    hoy = timezone.localdate()
    turnos_futuros = turnos.filter(fecha__gte=hoy)
    turnos_pasados = turnos.filter(fecha__lt=hoy)
    
    turnos.filter(
        cliente=request.user,
        visto_por_cliente=False
    ).update(visto_por_cliente=True)
    
    context = {
        'turnos_futuros': turnos_futuros,
        'turnos_pasados': turnos_pasados,
    }
    return render(request, 'mis_turnos.html', context)

@login_required
def confirmar_turno(request, turno_id):
    # Buscamos el turno, asegurándonos de que pertenece a un servicio del propietario logueado
    turno = get_object_or_404(Turno, id=turno_id, servicio__propietario=request.user)
    
    if request.method == 'POST':
        turno.estado = 'confirmado'
        turno.visto_por_cliente = False
        turno.save()
    
    # Redirigimos de vuelta al dashboard
    return redirect('dashboard_propietario')

@login_required
def cancelar_turno(request, turno_id):
    # Misma lógica de seguridad que en confirmar_turno
    turno = get_object_or_404(Turno, id=turno_id, servicio__propietario=request.user)
    
    if request.method == 'POST':
        turno.estado = 'cancelado'
        turno.visto_por_cliente = False
        turno.save()
        
    return redirect('dashboard_propietario')

@login_required
def obtener_notificaciones(request):
    """
    Una vista de API simple que devuelve el número de turnos
    confirmados o cancelados recientemente para el usuario.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'conteo': 0})
    
    # Buscamos turnos del usuario que hayan sido confirmados o cancelados
    # y que el usuario aún no ha "visto". Para esto necesitamos un nuevo campo.
    # Vamos a añadir un campo 'visto_por_cliente' al modelo Turno.
    conteo_notificaciones = Turno.objects.filter(
        cliente=request.user, 
        estado__in=['confirmado', 'cancelado'],
        visto_por_cliente=False # ¡Necesitamos añadir este campo!
    ).count()

    return JsonResponse({'conteo': conteo_notificaciones})

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        # Pasamos request.POST para procesar los datos enviados y 'instance'
        # para saber qué usuario estamos actualizando.
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            # Enviamos un mensaje de éxito que se mostrará en la plantilla
            messages.success(request, '¡Tu perfil ha sido actualizado correctamente!')
            return redirect('editar_perfil') # Redirigimos a la misma página
    else:
        # Si no es POST, simplemente mostramos el formulario con los datos actuales del usuario
        form = UserUpdateForm(instance=request.user)

    context = {
        'form': form
    }
    return render(request, 'editar_perfil.html', context)

# ========== INICIO DE LA MODIFICACIÓN ==========
# Vista de Login personalizada para tener control total sobre la redirección.
# Esto soluciona de forma definitiva el problema de redirección a /accounts/profile/
class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    # Forzamos la redirección a la página de inicio ('index') después de un login exitoso.
    success_url = reverse_lazy('index') 
    # Si un usuario ya logueado intenta ir a la página de login, lo redirigimos.
    redirect_authenticated_user = True
# ========== FIN DE LA MODIFICACIÓN ==========