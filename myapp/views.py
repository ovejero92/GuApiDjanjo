from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.forms import inlineformset_factory
from .models import Servicio, Turno, HorarioLaboral, SubServicio, Categoria
from .forms import BloqueoForm, TurnoForm, UserUpdateForm, IngresoTurnoForm, ReseñaForm, ServicioPersonalizacionForm, ServicioUpdateForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.db.models import Count, Sum,Avg
from django.db.models.functions import TruncDay
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
import json
from django.db.models import Q
from django.core.serializers import serialize
# ========== INICIO DE LA MODIFICACIÓN ==========
# Importaciones necesarias para la nueva vista de Login
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
# ========== FIN DE LA MODIFICACIÓN ==========

def index(request):
    categorias = Categoria.objects.all()
    categoria_seleccionada_slug = request.GET.get('categoria')

    if categoria_seleccionada_slug:
        # Filtramos los servicios por el slug de la categoría
        servicios = Servicio.objects.filter(categoria__slug=categoria_seleccionada_slug)
    else:
        # Si no hay filtro, mostramos todos
        servicios = Servicio.objects.all()

    context = {
        'servicios': servicios,
        'categorias': categorias,
        'categoria_activa': categoria_seleccionada_slug
    }
    return render(request, 'index.html', context)

def about(request):
    return render(request, 'about.html')

def terminos_y_condiciones(request):
    return render(request, 'terminos.html')

def politica_de_privacidad(request):
    return render(request, 'privacidad.html')

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

# --- VISTAS DEL DASHBOARD DEL PROPIETARIO (MODIFICADAS) ---
def get_servicio_activo(request):
    servicios_propietario = request.user.servicios_propios.all()
    if not servicios_propietario.exists():
        return None
    
    servicio_id_seleccionado = request.GET.get('servicio_id')
    if servicio_id_seleccionado:
        try:
            # Usamos get() que es más estricto que get_object_or_404 aquí
            servicio_activo = servicios_propietario.get(id=servicio_id_seleccionado)
        except Servicio.DoesNotExist:
            servicio_activo = servicios_propietario.first()
    else:
        servicio_activo = servicios_propietario.first()
    return servicio_activo

@login_required
def servicio_detail(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    
    if request.method == 'POST':
        # Al procesar el POST, le pasamos los datos del request.
        # El formulario se encargará de validar todo.
        form = TurnoForm(request.POST, servicio_id=servicio.id)
        if form.is_valid():
            # El método save() del formulario ahora hace todo el trabajo.
            turno = form.save(commit=False)
            turno.cliente = request.user # Asignamos el cliente logueado
            turno.save()
            form.save_m2m() # ¡Importante para guardar los sub-servicios!

            messages.success(request, "¡Turno solicitado con éxito!")
            return redirect('index')
    else:
        # Al mostrar la página por primera vez (GET)...
        # ========== INICIO DE LA CORRECCIÓN ==========
        # Ya no pasamos 'servicio=servicio', sino 'servicio_id=servicio.id'
        form = TurnoForm(servicio_id=servicio.id, initial={'fecha': timezone.localdate()})
        # ========== FIN DE LA CORRECCIÓN ==========

    # La lógica para reseñas y calificación promedio se queda igual.
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
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_turnos.html', {'no_hay_servicio': True})
    
    turnos = Turno.objects.filter(
        servicio=servicio_activo
    ).select_related('cliente').prefetch_related('sub_servicios_solicitados')

    # Obtenemos la fecha y hora actuales, conscientes de la zona horaria
    ahora = timezone.now()
    hoy = ahora.date()
    hora_actual = ahora.time()

    # --- LÓGICA DE FILTRADO MEJORADA ---
    # Pasados (Historial): Turnos de días anteriores O turnos de hoy cuya hora ya pasó.
    turnos_pasados = turnos.filter(
        Q(fecha__lt=hoy) | Q(fecha=hoy, hora__lt=hora_actual)
    ).order_by('-fecha', '-hora')

    # Próximos: Turnos de días futuros O turnos de hoy cuya hora aún no ha pasado.
    turnos_proximos = turnos.filter(
        Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora_actual)
    )
    
    # Pendientes y Confirmados se filtran a partir de la lista de Próximos
    turnos_pendientes = turnos_proximos.filter(estado='pendiente').order_by('fecha', 'hora')
    turnos_confirmados = turnos_proximos.filter(estado='confirmado').order_by('fecha', 'hora')
    
    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'turnos_pendientes': turnos_pendientes,
        'turnos_confirmados': turnos_confirmados,
        'turnos_pasados': turnos_pasados
    }
    return render(request, 'dashboard_turnos.html', context)

@login_required
def marcar_tour_visto(request):
    if request.method == 'POST':
        servicio = request.user.servicios_propios.first()
        if servicio:
            servicio.tour_completo = True
            servicio.save()
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)

# --- FUNCIÓN AUXILIAR PARA OBTENER EL SERVICIO ACTIVO ---
def get_servicio_activo(request):
    servicios_propietario = request.user.servicios_propios.all()
    if not servicios_propietario.exists():
        return None
    servicio_id_seleccionado = request.GET.get('servicio_id')
    if servicio_id_seleccionado:
        try:
            return servicios_propietario.get(id=servicio_id_seleccionado)
        except Servicio.DoesNotExist:
            return servicios_propietario.first()
    return servicios_propietario.first()

@login_required
def marcar_onboarding_completo(request):
    if request.method == 'POST':
        servicio = request.user.servicios_propios.first()
        if servicio:
            servicio.configuracion_inicial_completa = True
            servicio.save()
            return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def onboarding_propietario(request):
    servicio = request.user.servicios_propios.first()
    if not servicio:
        return redirect('index') # O a una página de "error"

    if servicio.configuracion_inicial_completa:
        return redirect('dashboard_turnos')

    UpdateForm = ServicioUpdateForm(prefix='detalles', instance=servicio)
    SubServicioFormSet = inlineformset_factory(Servicio, SubServicio, fields=('nombre', 'duracion', 'precio'), extra=1, can_delete=False)
    formset = SubServicioFormSet(prefix='catalogo', instance=servicio)

    if request.method == 'POST':
        update_form = ServicioUpdateForm(request.POST, prefix='detalles', instance=servicio)
        formset = SubServicioFormSet(request.POST, prefix='catalogo', instance=servicio)
        if update_form.is_valid() and formset.is_valid():
            update_form.save()
            formset.save()
            servicio.configuracion_inicial_completa = True
            servicio.save()
            messages.success(request, "¡Felicidades! Has completado la configuración inicial. Ahora, define tus horarios.")
            return redirect('dashboard_horarios')
    
    context = {'update_form': update_form, 'formset': formset}
    return render(request, 'onboarding.html', context)

@login_required
def dashboard_horarios(request):
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
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
    horario_formset = HorarioFormSet(prefix='horarios', instance=servicio_activo)
    bloqueo_form = BloqueoForm(prefix='bloqueo')
    
    if request.method == 'POST':
        # Verificamos qué formulario se envió
        if 'guardar_horarios' in request.POST:
            horario_formset = HorarioFormSet(request.POST, prefix='horarios', instance=servicio_activo)
            if horario_formset.is_valid():
                horario_formset.save()
                messages.success(request, "¡Horarios actualizados correctamente!")
                return redirect('dashboard_horarios')
        
        elif 'crear_bloqueo' in request.POST:
            bloqueo_form = BloqueoForm(request.POST, prefix='bloqueo')
            if bloqueo_form.is_valid():
                nuevo_bloqueo = bloqueo_form.save(commit=False)
                nuevo_bloqueo.servicio = servicio_activo
                nuevo_bloqueo.save()
                messages.success(request, "¡Nuevo bloqueo creado exitosamente!")
                return redirect('dashboard_horarios')

    # Obtenemos la lista de bloqueos existentes para mostrarlos
    bloqueos_existentes = servicio_activo.dias_no_disponibles.filter(fecha__gte=timezone.localdate()).order_by('fecha')

    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'formset': horario_formset,
        'bloqueo_form': bloqueo_form,
        'bloqueos': bloqueos_existentes,
    }
    return render(request, 'dashboard_horarios.html', context)

@login_required
def dashboard_metricas(request):
    # Obtener los servicios del propietario logueado
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_metricas.html', {'no_hay_servicio': True})
    
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
        'servicio_activo': servicio_activo,
        'ingresos_totales': agregados['ingresos_totales'] or 0,
        'turnos_totales': agregados['turnos_totales'] or 0,
        'ingreso_promedio': agregados['ingreso_promedio'] or 0,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
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
def dashboard_servicios(request): # Apariencia
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_servicios.html', {'no_hay_servicio': True})

    if request.method == 'POST':
        form = ServicioPersonalizacionForm(request.POST, request.FILES, instance=servicio_activo)
        if form.is_valid():
            form.save()
            messages.success(request, "¡La apariencia ha sido actualizada!")
            return redirect('dashboard_servicios')
    else:
        form = ServicioPersonalizacionForm(instance=servicio_activo)
    
    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'form': form
    }
    return render(request, 'dashboard_servicios.html', context)

@login_required
def dashboard_catalogo(request):
    # Usamos la función auxiliar para obtener el servicio que se está gestionando
    servicio_activo = get_servicio_activo(request)

    # Si el propietario no tiene ningún servicio, mostramos una página informativa
    if not servicio_activo:
        return render(request, 'dashboard_catalogo.html', {'no_hay_servicio': True})

    # Creamos el FormSet para el catálogo de sub-servicios
    SubServicioFormSet = inlineformset_factory(
        Servicio, SubServicio,
        fields=('nombre', 'descripcion', 'duracion', 'precio'),
        extra=1, can_delete=True
    )

    # Procesamiento del formulario POST
    if request.method == 'POST':
        # Instanciamos ambos formularios con los datos del POST
        update_form = ServicioUpdateForm(request.POST, instance=servicio_activo)
        formset = SubServicioFormSet(request.POST, instance=servicio_activo, prefix='subservicios')

        # Verificamos qué botón se presionó para saber qué formulario procesar
        if 'guardar_detalles' in request.POST:
            if update_form.is_valid():
                update_form.save()
                messages.success(request, "¡Los detalles de tu negocio han sido actualizados!")
                return redirect('dashboard_catalogo')
        
        elif 'guardar_catalogo' in request.POST:
            if formset.is_valid():
                formset.save()
                messages.success(request, "¡Catálogo de servicios actualizado!")
                return redirect('dashboard_catalogo')
    else:
        # Si es una petición GET, creamos formularios limpios ligados a la instancia
        update_form = ServicioUpdateForm(instance=servicio_activo)
        formset = SubServicioFormSet(instance=servicio_activo, prefix='subservicios')

    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'update_form': update_form,
        'formset': formset,
    }
    return render(request, 'dashboard_catalogo.html', context)

@login_required
def mis_turnos(request):
    turnos_del_cliente = request.user.turnos_solicitados.all()
    
    ahora = timezone.now()
    hoy = ahora.date()
    hora_actual = ahora.time()

    # --- LÓGICA DE FILTRADO MEJORADA (Idéntica a la del propietario) ---
    turnos_futuros = turnos_del_cliente.filter(
        Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora_actual)
    ).order_by('fecha', 'hora')

    turnos_pasados = turnos_del_cliente.filter(
        Q(fecha__lt=hoy) | Q(fecha=hoy, hora__lt=hora_actual)
    ).order_by('-fecha', '-hora')
    
    # Marcamos notificaciones como vistas (esto se queda igual)
    turnos_del_cliente.filter(visto_por_cliente=False).update(visto_por_cliente=True)
    
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
    turno = get_object_or_404(Turno, id=turno_id, servicio__propietario=request.user)
    
    if turno.estado in ['completado', 'cancelado']:
        messages.warning(request, "Este turno ya ha sido procesado.")
        return redirect('dashboard_turnos')

    if request.method == 'POST':
        form = IngresoTurnoForm(request.POST, instance=turno)
        if form.is_valid():
            instancia_turno = form.save(commit=False)
            instancia_turno.estado = 'completado'
            instancia_turno.save()
            messages.success(request, f"¡Turno de {turno.cliente.username} finalizado con éxito!")
            return redirect('dashboard_turnos')
    else:
        # ========== INICIO DE LA CORRECCIÓN ==========
        
        # Calculamos el precio sugerido sumando los precios de los sub-servicios solicitados.
        # .aggregate(Sum('precio')) devuelve un diccionario como {'precio__sum': 150.00}
        precio_sugerido_dict = turno.sub_servicios_solicitados.aggregate(total=Sum('precio'))
        precio_sugerido = precio_sugerido_dict['total'] or 0.00

        # Usamos este valor calculado como el valor inicial del formulario.
        # Si el turno ya tiene un ingreso_real guardado, se usará ese en su lugar.
        form = IngresoTurnoForm(instance=turno, initial={'ingreso_real': precio_sugerido})
        
        # ========== FIN DE LA CORRECCIÓN ==========

    context = {
        'form': form,
        'turno': turno
    }
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
    Calcula y devuelve los huecos de tiempo disponibles.
    Ahora acepta un parámetro 'duracion' para ser flexible.
    """
    fecha_str = request.GET.get('fecha')
    duracion_str = request.GET.get('duracion') # Recibimos la duración total calculada

    # Validación de que los parámetros necesarios llegaron
    if not fecha_str or not duracion_str:
        return JsonResponse({'error': 'Faltan parámetros de fecha o duración.'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        servicio = get_object_or_404(Servicio, id=servicio_id)
        duracion_requerida = int(duracion_str)
        if duracion_requerida <= 0:
            return JsonResponse({'error': 'Duración inválida.'}, status=400)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Parámetros inválidos.'}, status=400)

    # Lógica de cálculo de slots
    slots_disponibles = []
    
    try:
        horario_laboral = servicio.horarios.get(dia_semana=fecha.weekday(), activo=True)
    except HorarioLaboral.DoesNotExist:
        return JsonResponse({'slots': []}) # Día no laborable

    # Usamos la FK 'servicio' del modelo Turno para filtrar
    turnos_del_dia = Turno.objects.filter(servicio=servicio, fecha=fecha, estado__in=['pendiente', 'confirmado'])
    bloqueos_del_dia = servicio.dias_no_disponibles.filter(fecha=fecha)

    # ¡CORRECCIÓN CLAVE! Usamos la duración que nos llega por parámetro
    duracion_td = timedelta(minutes=duracion_requerida)
    
    hora_actual_dt = datetime.combine(fecha, horario_laboral.horario_apertura)
    hora_cierre_dt = datetime.combine(fecha, horario_laboral.horario_cierre)

    while hora_actual_dt + duracion_td <= hora_cierre_dt:
        slot_inicio = hora_actual_dt.time()
        slot_fin = (hora_actual_dt + duracion_td).time()
        
        slot_esta_disponible = True

        if fecha == timezone.localdate() and slot_inicio < timezone.localtime().time():
            slot_esta_disponible = False

        if slot_esta_disponible:
            for bloqueo in bloqueos_del_dia:
                if bloqueo.hora_inicio is None or (slot_inicio < bloqueo.hora_fin and slot_fin > bloqueo.hora_inicio):
                    slot_esta_disponible = False
                    break
        
        if slot_esta_disponible:
            for turno in turnos_del_dia:
                duracion_existente = timedelta(minutes=turno.duracion_total)
                turno_fin_existente = (datetime.combine(fecha, turno.hora) + duracion_existente).time()
                if slot_inicio < turno_fin_existente and slot_fin > turno.hora:
                    slot_esta_disponible = False
                    break
        
        if slot_esta_disponible:
            slots_disponibles.append(slot_inicio.strftime('%H:%M'))
        
        # Avanzamos en intervalos de 15 minutos para buscar más huecos. Puedes ajustar este valor.
        hora_actual_dt += timedelta(minutes=15)

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