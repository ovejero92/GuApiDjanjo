from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.forms import inlineformset_factory
from .models import Servicio, Turno, HorarioLaboral
from .forms import BloqueoForm, TurnoForm, UserUpdateForm, IngresoTurnoForm, ReseñaForm, CustomSignupForm, CustomSocialSignupForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.db.models import Count, Sum,Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
import json

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


# --- AÑADE ESTA NUEVA VISTA PARA LA ACTIVACIÓN ---
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, '¡Tu cuenta ha sido activada exitosamente!')
        return redirect('index')
    else:
        return render(request, 'registration/activacion_invalida.html')

@login_required
def servicio_detail(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        form = TurnoForm(request.POST, servicio=servicio)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.cliente = request.user
            turno.save() # La validación compleja ya está en el form.clean()
            messages.success(request, f"¡Turno solicitado con éxito para el {form.cleaned_data.get('fecha').strftime('%d/%m')} a las {form.cleaned_data.get('hora').strftime('%H:%M')}!")
            return redirect('index')
    else:
        form = TurnoForm(servicio=servicio, initial={'fecha': timezone.localdate()})

    reseñas = servicio.reseñas.all()
    calificacion_promedio = servicio.reseñas.aggregate(Avg('calificacion'))['calificacion__avg']
    
    context = {
        'servicio': servicio,
        'form': form,
        'reseñas': reseñas,
        'calificacion_promedio': calificacion_promedio,
    }
    return render(request, 'servicio_detail.html', context)
    
@login_required
def dashboard_turnos(request):
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
    return render(request, 'dashboard_turnos.html', context)

@login_required
def dashboard_horarios(request):
    # Asumimos por ahora que el propietario tiene UN SOLO servicio.
    # En el futuro, si un propietario puede tener varios, aquí habría un selector.
    try:
        servicio = request.user.servicios_propios.first()
    except AttributeError:
        # Manejo por si el usuario no tiene servicios (aunque no debería llegar aquí)
        servicio = None

    if not servicio:
        # Si no tiene servicios, no podemos mostrarle nada para configurar.
        return render(request, 'dashboard_horarios.html', {'no_hay_servicio': True})

    # --- LÓGICA DEL FORMULARIO DE HORARIOS SEMANALES ---
    # Creamos un FormSet para el modelo HorarioLaboral, vinculado a Servicio.
    # Esto nos permitirá editar los 7 días a la vez.
    HorarioFormSet = inlineformset_factory(
        Servicio,           # Modelo Padre
        HorarioLaboral,     # Modelo Hijo
        fields=('dia_semana','activo', 'horario_apertura', 'horario_cierre'), # Campos a editar
        extra=1,            # No mostrar formularios extra para añadir (ya deberían existir los 7)
        can_delete=True,   # No permitir borrar horarios (solo desactivar)
        widgets={
            'horario_apertura': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_cierre': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'dia_semana': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    )
    # --- Lógica de Bloqueos (Formulario simple y lista) ---
    # Creamos dos formularios distintos para no confundir el POST
    horario_formset = HorarioFormSet(prefix='horarios', instance=servicio)
    bloqueo_form = BloqueoForm(prefix='bloqueo')
    
    if request.method == 'POST':
        # Verificamos qué formulario se envió
        if 'guardar_horarios' in request.POST:
            horario_formset = HorarioFormSet(request.POST, prefix='horarios', instance=servicio)
            if horario_formset.is_valid():
                horario_formset.save()
                messages.success(request, "¡Horarios actualizados correctamente!")
                return redirect('dashboard_horarios')
        
        elif 'crear_bloqueo' in request.POST:
            bloqueo_form = BloqueoForm(request.POST, prefix='bloqueo')
            if bloqueo_form.is_valid():
                nuevo_bloqueo = bloqueo_form.save(commit=False)
                nuevo_bloqueo.servicio = servicio
                nuevo_bloqueo.save()
                messages.success(request, "¡Nuevo bloqueo creado exitosamente!")
                return redirect('dashboard_horarios')

    # Obtenemos la lista de bloqueos existentes para mostrarlos
    bloqueos_existentes = servicio.dias_no_disponibles.filter(fecha__gte=timezone.localdate()).order_by('fecha')

    context = {
        'servicio': servicio,
        'formset': horario_formset,
        'bloqueo_form': bloqueo_form,
        'bloqueos': bloqueos_existentes,
    }
    return render(request, 'dashboard_horarios.html', context)

@login_required
def dashboard_metricas(request):
    # Obtener los servicios del propietario logueado
    servicios_propietario = request.user.servicios_propios.all()

    # --- LÓGICA DE FILTRADO POR FECHAS ---
    # Por defecto, mostramos los últimos 30 días
    periodo = request.GET.get('periodo', '30d')
    hoy = timezone.localdate()
    
    if periodo == '7d':
        fecha_inicio = hoy - timedelta(days=6)
        titulo_periodo = "Últimos 7 días"
    elif periodo == 'mes_actual':
        fecha_inicio = hoy.replace(day=1)
        titulo_periodo = "Este Mes"
    elif periodo == 'año_actual':
        fecha_inicio = hoy.replace(day=1, month=1)
        titulo_periodo = "Este Año"
    else: # Por defecto y para '30d'
        fecha_inicio = hoy - timedelta(days=29)
        titulo_periodo = "Últimos 30 días"
    
    # QuerySet base: todos los turnos completados del propietario en el rango de fechas
    turnos_completados = Turno.objects.filter(
        servicio__in=servicios_propietario,
        estado='completado',
        fecha__gte=fecha_inicio,
        fecha__lte=hoy
    )

    # --- CÁLCULO DE MÉTRICAS CLAVE (TARJETAS) ---
    agregados = turnos_completados.aggregate(
        ingresos_totales=Sum('ingreso_real'),
        turnos_totales=Count('id'),
        ingreso_promedio=Avg('ingreso_real')
    )
    
    # --- DATOS PARA GRÁFICOS ---
    # Gráfico 1: Ingresos por día
    ingresos_por_dia = turnos_completados.annotate(
        dia=TruncDay('fecha')
    ).values('dia').annotate(
        total=Sum('ingreso_real')
    ).order_by('dia')
    
    labels_ingresos = [d['dia'].strftime('%d/%m') for d in ingresos_por_dia]
    data_ingresos = [float(d['total']) for d in ingresos_por_dia]

    # Gráfico 2: Servicios más populares en el período
    servicios_populares = turnos_completados.values(
        'servicio__nombre'
    ).annotate(
        cantidad=Count('id')
    ).order_by('-cantidad')[:5] # Top 5

    labels_servicios = [s['servicio__nombre'] for s in servicios_populares]
    data_servicios = [s['cantidad'] for s in servicios_populares]

    context = {
        'ingresos_totales': agregados['ingresos_totales'] or 0,
        'turnos_totales': agregados['turnos_totales'] or 0,
        'ingreso_promedio': agregados['ingreso_promedio'] or 0,
        
        # Datos para los gráficos, convertidos a JSON para JavaScript
        'labels_ingresos': json.dumps(labels_ingresos),
        'data_ingresos': json.dumps(data_ingresos),
        'labels_servicios': json.dumps(labels_servicios),
        'data_servicios': json.dumps(data_servicios),
        
        # Para el filtro de fechas
        'titulo_periodo': titulo_periodo,
        'periodo_seleccionado': periodo,
    }
    return render(request, 'dashboard_metricas.html', context)

@login_required
def dashboard_servicios(request):
    return render(request, 'dashboard_servicios.html')

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
def finalizar_turno(request, turno_id):
    # Misma seguridad: solo el propietario puede acceder.
    turno = get_object_or_404(Turno, id=turno_id, servicio__propietario=request.user)
    
    # Nos aseguramos de que no se pueda finalizar un turno que ya está 'cancelado' o 'completado'.
    if turno.estado in ['completado', 'cancelado']:
        messages.warning(request, "Este turno ya ha sido procesado.")
        return redirect('dashboard_turnos')

    if request.method == 'POST':
        form = IngresoTurnoForm(request.POST, instance=turno)
        if form.is_valid():
            # Guardamos la instancia del turno con el nuevo ingreso_real
            instancia_turno = form.save(commit=False)
            
            # ¡AQUÍ ESTÁ LA MAGIA!
            # En el mismo guardado, cambiamos el estado a 'completado'.
            instancia_turno.estado = 'completado'
            
            # Ahora sí, guardamos todo en la base de datos.
            instancia_turno.save()
            
            messages.success(request, f"¡Turno de {turno.cliente.username} finalizado con éxito!")
            return redirect('dashboard_turnos')
    else:
        # Al cargar la página por primera vez (GET), pre-llenamos el campo
        # de ingreso con el precio estándar del servicio para comodidad del propietario.
        form = IngresoTurnoForm(instance=turno, initial={'ingreso_real': turno.servicio.precio_estandar})

    context = {
        'form': form,
        'turno': turno
    }
    # Reutilizaremos la plantilla 'registrar_ingreso.html', pero ahora la llamaremos 'finalizar_turno.html'
    return render(request, 'finalizar_turno.html', context)

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
def obtener_slots_disponibles(request, servicio_id):
    """
    Calcula y devuelve los huecos de tiempo disponibles para un servicio y una fecha específicos,
    considerando horarios laborales, turnos existentes y días de bloqueo.
    """
    fecha_str = request.GET.get('fecha')
    
    if not fecha_str:
        return JsonResponse({'error': 'Falta el parámetro de fecha.'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        servicio = get_object_or_404(Servicio, id=servicio_id)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Formato de fecha o servicio inválido.'}, status=400)

    # --- INICIO DE LA LÓGICA DE CÁLCULO DE SLOTS ---
    slots_disponibles = []
    
    # 1. Obtener horario laboral para el día de la semana seleccionado
    dia_semana = fecha.weekday()  # Lunes=0, Domingo=6
    try:
        horario_laboral = servicio.horarios.get(dia_semana=dia_semana, activo=True)
    except HorarioLaboral.DoesNotExist:
        # Si el negocio no trabaja ese día, devolvemos una lista vacía.
        return JsonResponse({'slots': []})

    # 2. Obtener todos los turnos y bloqueos para ese día
    turnos_del_dia = list(Turno.objects.filter(servicio=servicio, fecha=fecha, estado__in=['pendiente', 'confirmado']))
    bloqueos_del_dia = servicio.dias_no_disponibles.filter(fecha=fecha)

    # 3. Iterar por el día en intervalos según la duración del servicio
    duracion_servicio = timedelta(minutes=servicio.duracion)
    
    # Combinamos la fecha con la hora para poder operar con datetimes
    hora_actual_dt = datetime.combine(fecha, horario_laboral.horario_apertura)
    hora_cierre_dt = datetime.combine(fecha, horario_laboral.horario_cierre)
    
    # Bucle para generar y validar cada posible slot
    while hora_actual_dt + duracion_servicio <= hora_cierre_dt:
        slot_inicio = hora_actual_dt.time()
        slot_fin = (hora_actual_dt + duracion_servicio).time()
        
        slot_esta_disponible = True

        # VALIDACIÓN A: No generar slots en el pasado
        if fecha == timezone.localdate() and slot_inicio < timezone.localtime().time():
            slot_esta_disponible = False

        # VALIDACIÓN B: Comprobar si se superpone con un turno existente
        if slot_esta_disponible:
            for turno in turnos_del_dia:
                turno_inicio_existente = turno.hora
                # Asumimos que la duración del turno existente es la del servicio actual
                duracion_existente = timedelta(minutes=servicio.duracion)
                turno_fin_existente = (datetime.combine(fecha, turno_inicio_existente) + duracion_existente).time()
                
                # Lógica de superposición de rangos
                if max(slot_inicio, turno_inicio_existente) < min(slot_fin, turno_fin_existente):
                    slot_esta_disponible = False
                    break

        # VALIDACIÓN C: Comprobar si se superpone con un bloqueo
        if slot_esta_disponible:
            for bloqueo in bloqueos_del_dia:
                if bloqueo.hora_inicio is None:  # Bloqueo de día completo
                    slot_esta_disponible = False
                    break
                # Bloqueo de franja horaria
                if max(slot_inicio, bloqueo.hora_inicio) < min(slot_fin, bloqueo.hora_fin):
                    slot_esta_disponible = False
                    break
        
        # Si el slot pasó todas las validaciones, se añade a la lista
        if slot_esta_disponible:
            slots_disponibles.append(slot_inicio.strftime('%H:%M'))
        
        # Avanzamos al siguiente posible slot
        hora_actual_dt += duracion_servicio

    return JsonResponse({'slots': slots_disponibles})

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

@login_required
def toggle_favorito(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    # request.user.servicios_favoritos es el 'related_name' que definimos
    if servicio in request.user.servicios_favoritos.all():
        # Si ya es favorito, lo quitamos
        request.user.servicios_favoritos.remove(servicio)
    else:
        # Si no es favorito, lo añadimos
        request.user.servicios_favoritos.add(servicio)
    
    # Redirigimos al usuario a la página desde donde vino (si es posible)
    # o a la página de inicio como fallback.
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def mis_favoritos(request):
    # Obtenemos solo los servicios que el usuario ha marcado
    servicios_favoritos = request.user.servicios_favoritos.all()
    context = {
        'servicios': servicios_favoritos
    }
    # Podemos reusar la plantilla index.html para mostrar las tarjetas
    return render(request, 'index.html', context)

@login_required
def crear_reseña(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, cliente=request.user)

    # Validaciones de seguridad:
    if turno.estado != 'completado':
        messages.error(request, "Solo puedes dejar una reseña para turnos completados.")
        return redirect('mis_turnos')
    if hasattr(turno, 'reseña'):
        messages.warning(request, "Ya has dejado una reseña para este turno.")
        return redirect('mis_turnos')

    if request.method == 'POST':
        form = ReseñaForm(request.POST)
        if form.is_valid():
            reseña = form.save(commit=False)
            reseña.turno = turno
            reseña.servicio = turno.servicio
            reseña.usuario = request.user
            reseña.save()
            messages.success(request, "¡Gracias por tu reseña!")
            return redirect('servicio_detail', servicio_id=turno.servicio.id)
    else:
        form = ReseñaForm()

    return render(request, 'crear_reseña.html', {'form': form, 'turno': turno})
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