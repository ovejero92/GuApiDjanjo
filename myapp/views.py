from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.forms import inlineformset_factory
from .models import Servicio, Turno, HorarioLaboral, SubServicio, Categoria, Plan, Suscripcion
from .forms import BloqueoForm, TurnoForm, UserUpdateForm, IngresoTurnoForm, ReseñaForm, ServicioPersonalizacionForm, ServicioUpdateForm, ServicioCreateForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import calendar
from django.db.models import Count, Sum,Avg,F, ExpressionWrapper, fields
from django.db.models.functions import TruncDay,TruncWeek, TruncMonth, TruncHour
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
import json
from django.db.models import Q
from django.core.serializers import serialize
from django.core.mail import send_mail
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse
from django.conf import settings
import mercadopago
from django.views.decorators.csrf import csrf_exempt


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

def crear_servicio_paso1(request):
    if request.user.is_authenticated:
        # Si ya está logueado, lo mandamos a crear el servicio
        return redirect('crear_servicio_paso2')
    else:
        # Si no, lo mandamos a registrarse primero.
        # El ?next=/crear-servicio/paso2/ le dice a Django que, después del login/signup,
        # lo redirija a la página de creación de servicio.
        return redirect(f"{reverse('account_signup')}?next={reverse('crear_servicio_paso2')}")

def about(request):
    return render(request, 'about.html')

def terminos_y_condiciones(request):
    return render(request, 'terminos.html')

def politica_de_privacidad(request):
    return render(request, 'privacidad.html')

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

def precios(request):
    try:
        context = {
            'plan_free': Plan.objects.get(slug='free'),
            'plan_pro': Plan.objects.get(slug='pro'),
            'plan_prime': Plan.objects.get(slug='prime'),
        }
    except Plan.DoesNotExist:
        messages.error(request, "Aún no se han configurado todos los planes de suscripción.")
        context = {'planes_no_configurados': True}

    return render(request, 'precios.html', context)

@login_required
def crear_servicio_paso2(request):
    # Comprobamos si el usuario ya tiene un servicio para no dejarle crear otro
    if request.user.servicios_propios.exists():
        messages.info(request, "Ya tienes un servicio gestionado. Aquí está tu dashboard.")
        return redirect('dashboard_propietario')

    if request.method == 'POST':
        form = ServicioCreateForm(request.POST)
        if form.is_valid():
            nuevo_servicio = form.save(commit=False)
            nuevo_servicio.propietario = request.user
            nuevo_servicio.save()
            
            messages.success(request, f"¡Felicidades! Tu negocio '{nuevo_servicio.nombre}' ha sido creado.")
            # Lo enviamos al onboarding o al dashboard
            return redirect('dashboard_propietario')
    else:
        form = ServicioCreateForm()

    return render(request, 'crear_servicio.html', {'form': form})

@login_required
def crear_suscripcion_mp(request, plan_slug):
    plan = get_object_or_404(Plan, slug=plan_slug)
    
    if not plan.mp_plan_id:
        messages.error(request, "Este plan no está configurado para pagos.")
        return redirect('precios')

    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    # Definimos el dominio base para las URLs de retorno
    base_url = "https://turnosok.com"
    if settings.DEBUG:
        base_url = "http://127.0.0.1:8000"

    preference_data = {
        "items": [
            {
                "id": plan.slug,
                "title": f"Suscripción Plan {plan.get_nombre_display()}",
                "description": f"Acceso mensual al plan {plan.get_nombre_display()} de TurnosOK.",
                "quantity": 1,
                "unit_price": float(plan.precio_mensual),
                "currency_id": "ARS",
            }
        ],
        "payer": {
            "email": request.user.email,
            "name": request.user.first_name,
            "surname": request.user.last_name,
        },
        "back_urls": {
            "success": f"{base_url}{reverse('pago_exitoso')}",
            "failure": f"{base_url}{reverse('precios')}",
            "pending": f"{base_url}{reverse('precios')}",
        },
        # ========== HEMOS ELIMINADO LA LÍNEA 'auto_return' ==========
        "preapproval_plan_id": plan.mp_plan_id,
    }
    
    # La llamada a la API sigue siendo la misma, pero ahora sin el parámetro conflictivo
    result = sdk.preference().create(preference_data)
    
    print("Respuesta de Mercado Pago:", result)
    
    if result and result.get("status") == 201:
        suscripcion_usuario, created = Suscripcion.objects.get_or_create(usuario=request.user)
        suscripcion_usuario.plan = plan
        suscripcion_usuario.is_active = False
        suscripcion_usuario.save()
        
        if settings.DEBUG:
            init_point = result["response"]["sandbox_init_point"]
        else:
            init_point = result["response"]["init_point"]
            
        return redirect(init_point)
    else:
        error_message = result.get("response", {}).get("message", "Intenta de nuevo.")
        messages.error(request, f"Hubo un error al crear la preferencia de pago: {error_message}")
        return redirect('precios')

@login_required
def pago_exitoso(request):
    messages.success(request, "¡Gracias por tu suscripción! Tu plan ha sido activado.")
    return redirect('dashboard_propietario') # O donde quieras

@csrf_exempt
def webhook_mp(request):
    # Esta vista es para que Mercado Pago nos notifique.
    # Es más avanzada y la implementaremos en un segundo paso si es necesario.
    # Por ahora, la activación es manual o al hacer el pago.
    return JsonResponse({"status": "ok"})

@login_required
def servicio_detail(request, servicio_slug):
    servicio = get_object_or_404(Servicio, slug=servicio_slug)
    
    if request.method == 'POST':
        # Al procesar el POST, le pasamos los datos del request.
        # El formulario se encargará de validar todo.
        form = TurnoForm(request.POST, servicio_id=servicio.id)
        if form.is_valid():
            # El método save() del formulario ahora hace todo el trabajo.
            sub_servicios_ids = request.POST.getlist('sub_servicios_solicitados')
            turno = form.save(commit=False)
            turno.cliente = request.user # Asignamos el cliente logueado
            turno.save()
            #form.save_m2m()  ¡Importante para guardar los sub-servicios!
            if sub_servicios_ids:
                turno.sub_servicios_solicitados.set(sub_servicios_ids)
            
            messages.success(request, "¡Turno solicitado con éxito!")
            return redirect('index')
    else:
        # Al mostrar la página por primera vez (GET)...
        # ========== INICIO DE LA CORRECCIÓN ==========
        # Ya no pasamos 'servicio=servicio', sino 'servicio_id=servicio.id'
        form = TurnoForm(servicio_id=servicio.id, initial={'fecha': timezone.localdate()})
        # ========== FIN DE LA CORRECCIÓN ==========

    # 1. Leemos el filtro de calificación desde la URL (ej: ?calificacion=5).
    calificacion_filtro = request.GET.get('calificacion')

    # 2. Creamos la consulta base para TODAS las reseñas de este servicio.
    reseñas_base = servicio.reseñas.all().select_related('usuario').order_by('-fecha_creacion')
    
    # 3. Contamos cuántas reseñas hay para cada estrella ANTES de aplicar el filtro.
    #    Esto es para poder mostrar "(10)" en el botón del filtro de 5 estrellas, etc.
    conteo_estrellas = reseñas_base.values('calificacion').annotate(count=Count('id'))
    conteo_map = {item['calificacion']: item['count'] for item in conteo_estrellas}
    conteo_total = reseñas_base.count()

    # 4. Aplicamos el filtro si el usuario seleccionó uno.
    if calificacion_filtro and calificacion_filtro.isdigit():
        reseñas_a_mostrar = reseñas_base.filter(calificacion=int(calificacion_filtro))
    else:
        reseñas_a_mostrar = reseñas_base
    
    # 5. Paginamos los resultados para obtener solo la PRIMERA página de reseñas.
    #    Mostraremos 6 reseñas inicialmente. Puedes cambiar este número.
    paginator = Paginator(reseñas_a_mostrar, 6)
    reseñas_iniciales = paginator.get_page(1)
    
    # ================================================================
    
    calificacion_promedio = servicio.reseñas.aggregate(Avg('calificacion'))['calificacion__avg']
    
    context = {
        'servicio': servicio,
        'form': form,
        'calificacion_promedio': calificacion_promedio,
        # DATOS NUEVOS PARA LA PLANTILLA
        'reseñas': reseñas_iniciales, # Le pasamos solo la primera página.
        'tiene_mas_paginas': reseñas_iniciales.has_next(), # True/False, para saber si mostrar el botón "Cargar más".
        'conteo_total_reseñas': conteo_total,
        'conteo_estrellas': conteo_map,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'filtro_activo': int(calificacion_filtro) if calificacion_filtro and calificacion_filtro.isdigit() else 0
    }
    return render(request, 'servicio_detail.html', context)

@login_required
def dashboard_turnos(request):
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_turnos.html', {'no_hay_servicio': True})
    
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo # Es buena práctica pasarlo también
        }
        return render(request, 'servicio_suspendido.html', context)
    
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo # Es buena práctica pasarlo también
        }
        return render(request, 'servicio_suspendido.html', context)
    
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
    turnos_pendientes = turnos_proximos.filter(estado='pendiente').order_by('fecha', 'hora').prefetch_related('sub_servicios_solicitados')
    turnos_confirmados = turnos_proximos.filter(estado='confirmado').order_by('fecha', 'hora').prefetch_related('sub_servicios_solicitados')
    
    # ================================================================
    # ========== NUEVA LÓGICA PARA EL HISTORIAL FILTRADO Y PAGINADO ==========
    # ================================================================

    # 1. Obtenemos el filtro activo desde la URL. Por defecto, mostramos los que están "para finalizar".
    filtro_historial_activo = request.GET.get('filtro_historial', 'por_finalizar')

    # 2. Creamos la consulta base para TODOS los turnos pasados.
    turnos_pasados_base = Turno.objects.filter(
        servicio=servicio_activo
    ).filter(
        Q(fecha__lt=hoy) | Q(fecha=hoy, hora__lt=ahora.time())
    ).select_related('cliente')

    # 3. Aplicamos el filtro correspondiente.
    if filtro_historial_activo == 'finalizados':
        # Mostramos los que ya están completados o cancelados, ordenados del más reciente al más antiguo.
        turnos_a_mostrar = turnos_pasados_base.filter(estado__in=['completado', 'cancelado']).order_by('-fecha', '-hora')
    else: # Por defecto, 'por_finalizar'
        # Mostramos los que pasaron pero siguen pendientes o confirmados, del más antiguo al más reciente.
        turnos_a_mostrar = turnos_pasados_base.filter(estado__in=['pendiente', 'confirmado']).order_by('fecha', 'hora')

    # 4. Aplicamos la paginación a la lista de turnos que hemos decidido mostrar.
    paginator = Paginator(turnos_a_mostrar, 10) # Mostraremos 10 turnos por página. Puedes cambiar este número.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'turnos_pendientes': turnos_pendientes, # Esto no cambia
        'turnos_confirmados': turnos_confirmados, # Esto no cambia
        'historial_page_obj': page_obj, # Pasamos el objeto de la página a la plantilla
        'filtro_historial_activo': filtro_historial_activo, # Le decimos a la plantilla qué botón resaltar
    }
    return render(request, 'dashboard_turnos.html', context)

@login_required
def dashboard_calendario(request):
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_calendario.html', {'no_hay_servicio': True})

    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
        }
        return render(request, 'servicio_suspendido.html', context)
    
    hoy = timezone.localdate()
    año = hoy.year
    mes = hoy.month

    primer_dia, num_dias = calendar.monthrange(año, mes)
    
    turnos_del_mes = Turno.objects.filter(
        servicio=servicio_activo,
        fecha__year=año,
        fecha__month=mes,
        estado__in=['confirmado', 'pendiente']
    ).prefetch_related('sub_servicios_solicitados')

    estado_dias = {}
    for dia_num in range(1, num_dias + 1):
        fecha_actual = datetime(año, mes, dia_num).date()
        turnos_del_dia = [t for t in turnos_del_mes if t.fecha == fecha_actual]
        
        # Obtenemos el conteo de turnos para este día
        conteo_turnos_dia = len(turnos_del_dia)

        if not turnos_del_dia:
            # Si no hay turnos, guardamos un diccionario con el estado y conteo 0
            estado_dias[dia_num] = {'estado': 'vacio', 'conteo': 0}
            continue

        # ==================== LÓGICA DE CÁLCULO DE OCUPACIÓN (SIN CAMBIOS) ====================
        try:
            horario_laboral = servicio_activo.horarios.get(dia_semana=fecha_actual.weekday(), activo=True)
            minutos_laborales = (datetime.combine(datetime.min, horario_laboral.horario_cierre) - 
                                datetime.combine(datetime.min, horario_laboral.horario_apertura)).seconds / 60
        except HorarioLaboral.DoesNotExist:
            minutos_laborales = 0

        if minutos_laborales > 0:
            minutos_reservados = sum(turno.duracion_total for turno in turnos_del_dia)
            porcentaje_ocupacion = (minutos_reservados / minutos_laborales) * 100
        else:
            porcentaje_ocupacion = 100
        # ====================================================================================

        # Determinamos el estado basado en la ocupación
        estado_css = 'con-turnos' # Valor por defecto si hay al menos un turno
        if porcentaje_ocupacion >= 90:
            estado_css = 'lleno'
        elif porcentaje_ocupacion >= 50:
            estado_css = 'casi-lleno'
        
        # Guardamos un diccionario con el estado CSS y el conteo de turnos
        estado_dias[dia_num] = {'estado': estado_css, 'conteo': conteo_turnos_dia}


    nombre_del_mes = calendar.month_name[mes]

    calendar_data_for_js = {
        'año': año,
        'mes': mes,
        'mes_nombre': nombre_del_mes,
    }

    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'año': año,
        'mes_nombre': nombre_del_mes,
        'rango_dias': range(1, num_dias + 1),
        'offset_dias': range(primer_dia),
        'estado_dias': estado_dias, # Ahora estado_dias contiene diccionarios
        'calendar_data': calendar_data_for_js,
    }
    
    return render(request, 'dashboard_calendario.html', context)

@login_required
def api_turnos_por_dia(request):
    """
    API que devuelve los detalles de los turnos de una fecha específica.
    """
    fecha_str = request.GET.get('fecha')
    servicio_activo = get_servicio_activo(request)

    if not fecha_str or not servicio_activo:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)

    turnos = Turno.objects.filter(
        servicio=servicio_activo,
        fecha=fecha,
        estado__in=['confirmado', 'pendiente']
    ).select_related('cliente').prefetch_related('sub_servicios_solicitados').order_by('hora')

    # Preparamos los datos para enviarlos como JSON
    datos_turnos = []
    for turno in turnos:
        servicios = [s.nombre for s in turno.sub_servicios_solicitados.all()]
        datos_turnos.append({
            'hora': turno.hora.strftime('%H:%M'),
            'cliente': turno.cliente.first_name or turno.cliente.username,
            'estado': turno.get_estado_display(),
            'servicios': servicios,
        })
    
    return JsonResponse({'turnos': datos_turnos})

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
    
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo # Es buena práctica pasarlo también
        }
        return render(request, 'servicio_suspendido.html', context)
    
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
    try:
        tiene_acceso = request.user.suscripcion.plan.allow_metrics
    except (Suscripcion.DoesNotExist, AttributeError):
        tiene_acceso = False
    
    if not tiene_acceso and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Si no tiene acceso, no le devolvemos datos para los gráficos.
        return JsonResponse({'error': 'Acceso denegado'}, status=403)
    
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_metricas.html', {'no_hay_servicio': True})
    
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo,
            'tiene_acceso': tiene_acceso
        }
        return render(request, 'servicio_suspendido.html', context)
    
    # --- LÓGICA DE API PARA EL GRÁFICO DE INGRESOS (AJAX) ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        agrupar_por = request.GET.get('agrupar_por', 'dia')
        hoy = timezone.localdate()
        qs = Turno.objects.filter(servicio=servicio_activo, estado='completado')
        
        if agrupar_por == 'dia':
            fecha_str = request.GET.get('fecha', hoy.strftime('%Y-%m-%d'))
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            datos = qs.filter(fecha=fecha).annotate(periodo=TruncHour('hora')).values('periodo').annotate(total=Sum('ingreso_real')).order_by('periodo')
            labels = [d['periodo'].strftime('%H:%M hs') for d in datos]
        elif agrupar_por == 'mes':
            mes_str = request.GET.get('mes', hoy.strftime('%Y-%m'))
            mes = datetime.strptime(mes_str, '%Y-%m')
            datos = qs.filter(fecha__year=mes.year, fecha__month=mes.month).annotate(periodo=TruncDay('fecha')).values('periodo').annotate(total=Sum('ingreso_real')).order_by('periodo')
            labels = [d['periodo'].strftime('%d/%m') for d in datos]
        else: # año
            año_str = request.GET.get('año', str(hoy.year))
            año = int(año_str)
            datos = qs.filter(fecha__year=año).annotate(periodo=TruncMonth('fecha')).values('periodo').annotate(total=Sum('ingreso_real')).order_by('periodo')
            labels = [d['periodo'].strftime('%b %Y') for d in datos]

        data_puntos = [float(d['total']) if d['total'] else 0 for d in datos]
        return JsonResponse({'labels': labels, 'data': data_puntos})

    periodo = request.GET.get('periodo', '30d') # <-- Leemos el período para las tarjetas
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
    else:
        fecha_inicio = hoy - timedelta(days=29)
        titulo_periodo = "Últimos 30 días"

    # -- Cálculo de tarjetas de KPI --
    turnos_completados_periodo = Turno.objects.filter(
        servicio=servicio_activo, 
        estado='completado',
        fecha__gte=fecha_inicio,
        fecha__lte=hoy
    )
    agregados = turnos_completados_periodo.aggregate(
        ingresos_totales=Sum('ingreso_real'),
        turnos_totales=Count('id'),
        ingreso_promedio=Avg('ingreso_real')
    )
    
    # -- Cálculo de servicios populares (sobre el total histórico) --
    contador_servicios = {}
    for turno in turnos_completados_periodo.prefetch_related('sub_servicios_solicitados'):
        for sub_servicio in turno.sub_servicios_solicitados.all():
            nombre = sub_servicio.nombre
            contador_servicios[nombre] = contador_servicios.get(nombre, 0) + 1
    
    servicios_populares_ordenados = sorted(contador_servicios.items(), key=lambda item: item[1], reverse=True)[:5]
    labels_servicios = [item[0] for item in servicios_populares_ordenados]
    data_servicios = [item[1] for item in servicios_populares_ordenados]

    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'ingresos_totales': agregados['ingresos_totales'] or 0,
        'turnos_totales': agregados['turnos_totales'] or 0,
        'ingreso_promedio': agregados['ingreso_promedio'] or 0,
        'labels_servicios_json': json.dumps(labels_servicios),
        'data_servicios_json': json.dumps(data_servicios),
        'titulo_periodo': titulo_periodo,
        'periodo_seleccionado': periodo,
    }
    return render(request, 'dashboard_metricas.html', context)

@login_required
def dashboard_servicios(request): # Apariencia
    try:
        tiene_acceso = request.user.suscripcion.plan.allow_customization
    except (Suscripcion.DoesNotExist, AttributeError):
        tiene_acceso = False
    
    if not tiene_acceso and request.method == 'POST':
        # Si no tiene acceso, no le permitimos guardar cambios.
        return redirect('precios')
    
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_servicios.html', {'no_hay_servicio': True})
    
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo # Es buena práctica pasarlo también
        }
        return render(request, 'servicio_suspendido.html', context)

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
        'form': form,
        'tiene_acceso': tiene_acceso
    }
    return render(request, 'dashboard_servicios.html', context)

@login_required
def dashboard_catalogo(request):
    # Usamos la función auxiliar para obtener el servicio que se está gestionando
    servicio_activo = get_servicio_activo(request)

    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo # Es buena práctica pasarlo también
        }
        return render(request, 'servicio_suspendido.html', context)
    
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
        # Esta vista ahora SOLO maneja el formset del catálogo
        formset = SubServicioFormSet(request.POST, instance=servicio_activo, prefix='subservicios')
        if formset.is_valid():
            formset.save()
            messages.success(request, "¡Catálogo de servicios actualizado!")
            return redirect('dashboard_catalogo')
    else:
        formset = SubServicioFormSet(instance=servicio_activo, prefix='subservicios')

    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'formset': formset,
    }
    return render(request, 'dashboard_catalogo.html', context)

@login_required
def dashboard_detalles_negocio(request):
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_detalles_negocio.html', {'no_hay_servicio': True})

    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True, # Le decimos a la plantilla que el tour YA se hizo.
            'servicio_activo': servicio_activo # Es buena práctica pasarlo también
        }
        return render(request, 'servicio_suspendido.html', context)
    
    if request.method == 'POST':
        form = ServicioUpdateForm(request.POST, instance=servicio_activo)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Los detalles de tu negocio han sido actualizados!")
            return redirect('dashboard_detalles_negocio')
    else:
        form = ServicioUpdateForm(instance=servicio_activo)

    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'update_form': form,
    }
    return render(request, 'dashboard_detalles_negocio.html', context)

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
    
        try:
            asunto = f"¡Tu turno en {turno.servicio.nombre} ha sido confirmado!"
            mensaje = (
                f"Hola {turno.cliente.first_name},\n\n"
                f"Buenas noticias. Tu turno para el día {turno.fecha.strftime('%d/%m/%Y')} a las {turno.hora.strftime('%H:%M')} hs "
                f"en '{turno.servicio.nombre}' ha sido confirmado por el propietario.\n\n"
                f"Puedes ver todos tus turnos en tu perfil.\n\n"
                f"¡Te esperamos!"
            )
            
            send_mail(
                asunto,
                mensaje,
                None,  # Django usará el DEFAULT_FROM_EMAIL de tus settings
                [turno.cliente.email],
                fail_silently=False,
            )
            messages.success(request, f"Turno confirmado y notificación enviada a {turno.cliente.first_name}.")
        except Exception as e:
            # Si el email falla, no queremos que la app se rompa.
            # Simplemente informamos al propietario del error.
            messages.error(request, f"El turno fue confirmado, pero hubo un error al enviar el email de notificación: {e}")
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
        
        try:
            asunto = f"Información importante sobre tu turno en {turno.servicio.nombre}"
            mensaje = (
                f"Hola {turno.cliente.first_name},\n\n"
                f"Te informamos que tu turno para el día {turno.fecha.strftime('%d/%m/%Y')} a las {turno.hora.strftime('%H:%M')} hs "
                f"en '{turno.servicio.nombre}' ha sido cancelado por el propietario.\n\n"
                f"Si crees que esto es un error o quieres reprogramar, por favor, ponte en contacto directamente con el negocio.\n\n"
                f"Lamentamos las molestias."
            )
            
            send_mail(
                asunto,
                mensaje,
                None,
                [turno.cliente.email],
                fail_silently=False,
            )
            messages.info(request, f"Turno cancelado y notificación enviada a {turno.cliente.first_name}.")
        except Exception as e:
            messages.error(request, f"El turno fue cancelado, pero hubo un error al enviar el email de notificación: {e}")
            
    return redirect('dashboard_propietario')

@login_required
def finalizar_turno(request, turno_id):
    turno = get_object_or_404(Turno, id=turno_id, servicio__propietario=request.user)
    servicio_activo = turno.servicio

    if turno.estado == 'cancelado':
        messages.warning(request, "No se puede procesar un turno que ha sido cancelado.")
        return redirect('dashboard_turnos')

    if request.method == 'POST':
        form = IngresoTurnoForm(request.POST, instance=turno)
        if form.is_valid():
            instancia_turno = form.save(commit=False)
            
            # Siempre nos aseguramos de que el estado final sea 'completado'.
            instancia_turno.estado = 'completado'
            instancia_turno.save()

            # Mensaje dinámico dependiendo de la acción
            if turno.ingreso_real is None:
                messages.success(request, f"¡Turno de {turno.cliente.username} finalizado con éxito!")
            else:
                messages.success(request, f"¡Ingreso del turno actualizado correctamente!")

            return redirect('dashboard_turnos')
    else:
        # Si el turno ya tiene un ingreso, lo usamos. Si no, calculamos el sugerido.
        if turno.ingreso_real is not None:
            # El turno ya fue finalizado, estamos editando.
            form = IngresoTurnoForm(instance=turno)
        else:
            # Es la primera vez que se finaliza, calculamos el precio sugerido.
            precio_sugerido_dict = turno.sub_servicios_solicitados.aggregate(total=Sum('precio'))
            precio_sugerido = precio_sugerido_dict.get('total') or 0.00
            form = IngresoTurnoForm(instance=turno, initial={'ingreso_real': precio_sugerido})

    # Decidimos el título de la página según si estamos finalizando o editando
    titulo_pagina = "Editar Ingreso del Turno" if turno.ingreso_real is not None else "Finalizar y Registrar Ingreso"

    context = {
        'form': form,
        'turno': turno,
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'titulo_pagina': titulo_pagina, # Pasamos el título dinámico a la plantilla
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

def api_get_reseñas(request, servicio_slug):
    servicio = get_object_or_404(Servicio, slug=servicio_slug)
    
    # Obtenemos todos los filtros de la URL
    calificacion_filtro = request.GET.get('calificacion')
    page_number = request.GET.get('page', 1)

    # Creamos la consulta base
    reseñas_list = servicio.reseñas.all().select_related('usuario').order_by('-fecha_creacion')

    # Aplicamos el filtro si existe
    if calificacion_filtro and calificacion_filtro.isdigit():
        reseñas_list = reseñas_list.filter(calificacion=int(calificacion_filtro))

    # Paginamos los resultados
    paginator = Paginator(reseñas_list, 4) # Mostraremos 4 reseñas por cada "Cargar más"
    page_obj = paginator.get_page(page_number)

    # Preparamos los datos para convertirlos a JSON
    data = {
        'reseñas': [
            {
                'usuario': reseña.usuario.username,
                'fecha_creacion': reseña.fecha_creacion.strftime('%d/%m/%Y'),
                'calificacion': reseña.calificacion,
                'comentario': reseña.comentario,
            } for reseña in page_obj
        ],
        'has_next_page': page_obj.has_next()
    }
    
    return JsonResponse(data)

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
            return redirect('servicio_detail', servicio_slug=turno.servicio.slug)
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