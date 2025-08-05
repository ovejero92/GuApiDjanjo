from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.forms import inlineformset_factory, modelformset_factory
from .models import Servicio, Profesional , Turno, HorarioLaboral, SubServicio, Categoria, Plan, Suscripcion, DiaNoDisponible
from .forms import BloqueoForm, ProfesionalForm, HorarioLaboralFormSet , HorarioLaboralForm, TurnoForm, UserUpdateForm, IngresoTurnoForm, ReseñaForm, ServicioPersonalizacionForm, ServicioUpdateForm, ServicioCreateForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import calendar
from django.db.models import Count, Sum,Avg
from django.db.models.functions import TruncDay, TruncMonth, TruncHour
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
import json
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.core.mail import send_mail
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy, reverse
from django.conf import settings
import mercadopago
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string

def index(request):
    categorias_con_servicios = Categoria.objects.annotate(
        num_servicios=Count('servicios')
    ).filter(num_servicios__gt=0)

    categoria_seleccionada_slug = request.GET.get('categoria')
    search_query = request.GET.get('q', None)
    
    servicios = Servicio.objects.filter(esta_activo=True)

    if categoria_seleccionada_slug:
        servicios = servicios.filter(categoria__slug=categoria_seleccionada_slug)

    if search_query:
        servicios = servicios.filter(nombre__icontains=search_query)

    context = {
        'servicios': servicios,
        'categorias': categorias_con_servicios,
        'categoria_activa': categoria_seleccionada_slug,
        'search_query': search_query,
    }
    return render(request, 'index.html', context)

def crear_servicio_paso1(request):
    if request.user.is_authenticated:
        return redirect('crear_servicio_paso2')
    else:
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
    if request.user.servicios_propios.exists():
        messages.info(request, "Ya tienes un servicio gestionado. Aquí está tu dashboard.")
        return redirect('dashboard_propietario')

    if request.method == 'POST':
        form = ServicioCreateForm(request.POST)
        if form.is_valid():
            servicio = form.save(commit=False)
            servicio.propietario = request.user
            servicio.save()
            profesional_propietario, created = Profesional.objects.get_or_create(
                servicio=servicio,
                nombre=request.user.first_name or request.user.username, # Usamos su nombre
                email=request.user.email,
                user_account=request.user
            )
            HorarioLaboral.objects.create(
                profesional=profesional_propietario,
                activo=True,
                lunes=True, martes=True, miercoles=True, jueves=True, viernes=True, # L-V por defecto
                horario_apertura='09:00:00',
                horario_cierre='18:00:00',
                tiene_descanso=False
            )
            return redirect('dashboard_propietario')
    else:
        form = ServicioCreateForm()

    return render(request, 'crear_servicio.html', {'form': form})

@login_required
def crear_suscripcion_mp(request, plan_slug):
    plan = get_object_or_404(Plan, slug=plan_slug)
    
    if not plan.mp_plan_id:
        messages.error(request, "Este plan no está configurado para pagos online.")
        return redirect('precios')

    suscripcion_usuario, created = Suscripcion.objects.get_or_create(
        usuario=request.user,
        defaults={'plan': plan, 'is_active': False}
    )
    if not created:
        suscripcion_usuario.plan = plan
        suscripcion_usuario.save()
    
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    base_url = "https://turnosok.com"
    if settings.DEBUG:
        base_url = "http://127.0.0.1:8000"

    preapproval_data = {
        "preapproval_plan_id": plan.mp_plan_id,
        "payer_email": request.user.email,
        "back_urls": {
            "success": f"{base_url}{reverse('pago_exitoso')}",
            "failure": f"{base_url}{reverse('precios')}",
            "pending": f"{base_url}{reverse('precios')}",
        },
        "auto_return": "approved",
        "external_reference": str(suscripcion_usuario.id)
    }

    result = sdk.preapproval().create(preapproval_data)
    
    print("Respuesta de Suscripción de Mercado Pago:", result)

    if result and result.get("status") == 201:
        mp_id_suscripcion = result["response"]["id"]
        
        suscripcion_usuario.mp_subscription_id = mp_id_suscripcion
        suscripcion_usuario.is_active = False
        suscripcion_usuario.save()
        
        if settings.DEBUG:
            init_point = result["response"]["sandbox_init_point"]
        else:
            init_point = result["response"]["init_point"]
            
        return redirect(init_point)
    else:
        error_message = result.get("response", {}).get("message", "Intenta de nuevo.")
        messages.error(request, f"Hubo un error al crear la suscripción: {error_message}")
        return redirect('precios')

@login_required
def pago_exitoso(request):
    messages.success(request, "¡Gracias por tu suscripción! Tu plan ha sido activado.")
    if request.user.servicios_propios.exists():
        return redirect('dashboard_propietario')
    else:
        return redirect('crear_servicio_paso2')

@csrf_exempt
def webhook_mp(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        if data.get("type") == "preapproval":
            mp_subscription_id = data.get("data", {}).get("id")
            try:
                sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
                subscription_data = sdk.preapproval().get(mp_subscription_id)
                if subscription_data and subscription_data.get("status") == 200:
                    response_data = subscription_data.get("response", {})
                    try:
                        suscripcion = Suscripcion.objects.get(mp_subscription_id=response_data.get("id"))
                        if response_data.get("status") == "authorized":
                            if not suscripcion.is_active:
                                if not suscripcion.ha_visto_animacion_premium:
                                    suscripcion.ha_visto_animacion_premium = True
                            suscripcion.is_active = True
                        else:
                            suscripcion.is_active = False
                        suscripcion.save()
                    except Suscripcion.DoesNotExist:
                        pass
            except Exception as e:
                print(f"Error al procesar webhook de MP: {e}")
    return JsonResponse({"status": "received"})

@login_required
def servicio_detail(request, servicio_slug):
    servicio = get_object_or_404(Servicio, slug=servicio_slug)

    if request.method == 'POST':
        form = TurnoForm(request.POST, servicio=servicio)
        if form.is_valid():
            profesional_id = request.POST.get('profesional_id')
            profesional_asignado = None
            if profesional_id:
                try:
                    profesional_asignado = Profesional.objects.get(id=profesional_id, servicio=servicio)
                except Profesional.DoesNotExist:
                    messages.error(request, 'El profesional seleccionado no es válido.')
                    return redirect('servicio_detail', servicio_slug=servicio_slug)
            
            if not profesional_asignado:
                messages.error(request, 'No se pudo asignar un profesional al turno. Por favor, contacte a soporte.')
                return redirect('servicio_detail', servicio_slug=servicio_slug)

            turno = form.save(commit=False)
            turno.cliente = request.user
            turno.servicio = servicio
            turno.profesional = profesional_asignado
            turno.save()
            form.save_m2m()
            
            propietario = servicio.propietario
            enviar_email = False
            try:
                suscripcion = getattr(propietario, 'suscripcion', None)
                if suscripcion and suscripcion.is_active and suscripcion.plan.slug != 'free':
                    enviar_email = True
            except AttributeError:
                pass

            if enviar_email:
                try:
                    asunto = f"¡Nuevo Turno Reservado en {servicio.nombre}!"
                    contexto_email = {'turno': turno, 'servicio': servicio, 'cliente': request.user, 'profesional_asignado': profesional_asignado, 'domain': request.get_host()}
                    mensaje_texto = render_to_string('emails/nuevo_turno_propietario.txt', contexto_email)
                    mensaje_html = render_to_string('emails/nuevo_turno_propietario.html', contexto_email)
                    send_mail(asunto, mensaje_texto, settings.DEFAULT_FROM_EMAIL, [propietario.email], html_message=mensaje_html)
                except Exception as e:
                    print(f"Error al enviar email de nuevo turno: {e}")
            
            messages.success(request, "¡Turno solicitado con éxito!")
            return redirect('mis_turnos')
    else:
        form = TurnoForm(servicio=servicio)

    profesionales = servicio.profesionales.filter(activo=True)
    reglas_horario_activas = HorarioLaboral.objects.filter(profesional__in=profesionales, activo=True)

    dias_laborables_js = {str(i): False for i in range(7)}
    for regla in reglas_horario_activas:
        if regla.domingo: dias_laborables_js['0'] = True
        if regla.lunes: dias_laborables_js['1'] = True
        if regla.martes: dias_laborables_js['2'] = True
        if regla.miercoles: dias_laborables_js['3'] = True
        if regla.jueves: dias_laborables_js['4'] = True
        if regla.viernes: dias_laborables_js['5'] = True
        if regla.sabado: dias_laborables_js['6'] = True
    
    turnos_reservados = Turno.objects.filter(servicio=servicio, estado__in=['pendiente', 'confirmado'])
    fechas_ocupadas = [turno.fecha.strftime('%Y-%m-%d') for turno in turnos_reservados]

    reseñas_base = servicio.reseñas.all().select_related('usuario').order_by('-fecha_creacion')
    calificacion_promedio = reseñas_base.aggregate(Avg('calificacion'))['calificacion__avg']
    conteo_total = reseñas_base.count()
    conteo_estrellas = reseñas_base.values('calificacion').annotate(count=Count('id'))
    conteo_map = {item['calificacion']: item['count'] for item in conteo_estrellas}

    calificacion_filtro = request.GET.get('calificacion')
    if calificacion_filtro and calificacion_filtro.isdigit():
        reseñas_a_mostrar = reseñas_base.filter(calificacion=int(calificacion_filtro))
    else:
        reseñas_a_mostrar = reseñas_base

    paginator = Paginator(reseñas_a_mostrar, 6)
    reseñas_iniciales = paginator.get_page(1)
    
    context = {
        'servicio': servicio,
        'form': form,
        'profesionales': profesionales,
        'calificacion_promedio': calificacion_promedio,
        'reseñas': reseñas_iniciales,
        'tiene_mas_paginas': reseñas_iniciales.has_next(),
        'conteo_total_reseñas': conteo_total,
        'conteo_estrellas': conteo_map,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
        'filtro_activo': int(calificacion_filtro) if calificacion_filtro and calificacion_filtro.isdigit() else 0,
        'horario_trabajo_json': json.dumps(dias_laborables_js),
        'fechas_ocupadas_json': json.dumps(fechas_ocupadas),
    }
    return render(request, 'servicio_detail.html', context)

@login_required
def dashboard_turnos(request):
    mostrar_animacion = False
    try:
        suscripcion = request.user.suscripcion
        if suscripcion.is_active and not suscripcion.ha_visto_animacion_premium:
            mostrar_animacion = True
            suscripcion.ha_visto_animacion_premium = True
            suscripcion.save()
    except (Suscripcion.DoesNotExist, AttributeError):
        pass
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_turnos.html', {'no_hay_servicio': True, 'mostrar_animacion': mostrar_animacion})
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
        }
        return render(request, 'servicio_suspendido.html', context)
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
        }
        return render(request, 'servicio_suspendido.html', context)
    turnos = Turno.objects.filter(
        servicio=servicio_activo
    ).select_related('cliente').prefetch_related('sub_servicios_solicitados')
    ahora = timezone.now()
    hoy = ahora.date()
    hora_actual = ahora.time()
    turnos_pasados = turnos.filter(
        Q(fecha__lt=hoy) | Q(fecha=hoy, hora__lt=hora_actual)
    ).order_by('-fecha', '-hora')
    turnos_proximos = turnos.filter(
        Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora_actual)
    )
    turnos_pendientes = turnos_proximos.filter(estado='pendiente').order_by('fecha', 'hora').prefetch_related('sub_servicios_solicitados')
    turnos_confirmados = turnos_proximos.filter(estado='confirmado').order_by('fecha', 'hora').prefetch_related('sub_servicios_solicitados')
    filtro_historial_activo = request.GET.get('filtro_historial', 'por_finalizar')
    turnos_pasados_base = Turno.objects.filter(
        servicio=servicio_activo
    ).filter(
        Q(fecha__lt=hoy) | Q(fecha=hoy, hora__lt=ahora.time())
    ).select_related('cliente')
    if filtro_historial_activo == 'finalizados':
        turnos_a_mostrar = turnos_pasados_base.filter(estado__in=['completado', 'cancelado']).order_by('-fecha', '-hora')
    else:
        turnos_a_mostrar = turnos_pasados_base.filter(estado__in=['pendiente', 'confirmado']).order_by('fecha', 'hora')
    paginator = Paginator(turnos_a_mostrar, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'turnos_pendientes': turnos_pendientes,
        'turnos_confirmados': turnos_confirmados,
        'historial_page_obj': page_obj,
        'filtro_historial_activo': filtro_historial_activo,
        'mostrar_animacion': mostrar_animacion,
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
    primer_dia_semana, num_dias = calendar.monthrange(año, mes)
    
    turnos_del_mes = Turno.objects.filter(
        servicio=servicio_activo,
        fecha__year=año,
        fecha__month=mes,
        estado__in=['confirmado', 'pendiente']
    ).prefetch_related('sub_servicios_solicitados')
    profesionales_del_servicio = servicio_activo.profesionales.all()

    estado_dias = {}
    for dia_num in range(1, num_dias + 1):
        fecha_actual = datetime(año, mes, dia_num).date()
        turnos_del_dia = [t for t in turnos_del_mes if t.fecha == fecha_actual]
        conteo_turnos_dia = len(turnos_del_dia)

        if not turnos_del_dia:
            estado_dias[dia_num] = {'estado': 'vacio', 'conteo': 0}
            continue

        # Calculamos los minutos laborales totales de TODOS los profesionales para ese día
        minutos_laborales_totales_del_dia = 0
        for prof in profesionales_del_servicio:
            try:
                dia_de_la_semana_num = fecha_actual.weekday()
                dia_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'}
                campo_dia_a_filtrar = dia_map.get(dia_de_la_semana_num)
                
                # ¡Buscamos la regla del PROFESIONAL!
                regla_horario = prof.horarios.filter(activo=True, **{campo_dia_a_filtrar: True}).first()

                if regla_horario:
                    minutos_jornada = (datetime.combine(datetime.min, regla_horario.horario_cierre) - 
                                           datetime.combine(datetime.min, regla_horario.horario_apertura)).seconds / 60
                    minutos_descanso = 0
                    if regla_horario.tiene_descanso and regla_horario.descanso_inicio and regla_horario.descanso_fin:
                        minutos_descanso = (datetime.combine(datetime.min, regla_horario.descanso_fin) -
                                            datetime.combine(datetime.min, regla_horario.descanso_inicio)).seconds / 60
                    minutos_laborales_totales_del_dia += (minutos_jornada - minutos_descanso)
            except HorarioLaboral.DoesNotExist:
                continue # Este profesional no trabaja ese día
        
        # El resto de tu lógica de cálculo de porcentaje de ocupación usa el nuevo total
        if minutos_laborales_totales_del_dia > 0:
            minutos_reservados = sum(turno.duracion_total for turno in turnos_del_dia)
            porcentaje_ocupacion = (minutos_reservados / minutos_laborales_totales_del_dia) * 100
        else:
            porcentaje_ocupacion = 100
        estado_css = 'con-turnos'
        if porcentaje_ocupacion >= 90:
            estado_css = 'lleno'
        elif porcentaje_ocupacion >= 50:
            estado_css = 'casi-lleno'
        estado_dias[dia_num] = {'estado': estado_css, 'conteo': conteo_turnos_dia}
    nombre_del_mes = calendar.month_name[mes].capitalize()
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
        'offset_dias': range(primer_dia_semana),
        'estado_dias': estado_dias,
        'calendar_data': calendar_data_for_js,
    }
    return render(request, 'dashboard_calendario.html', context)

@login_required
def api_turnos_por_dia(request):
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
        return redirect('index')
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
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
        }
        return render(request, 'servicio_suspendido.html', context)
    
    profesional_a_gestionar = servicio_activo.profesionales.first()

    if not profesional_a_gestionar:
        messages.warning(request, "Este servicio no tiene ningún profesional asignado. No se pueden gestionar horarios.")
        return render(request, 'dashboard/horarios.html', {'servicio_activo': servicio_activo, 'no_hay_profesional': True})

    HorarioFormSet = modelformset_factory(
        HorarioLaboral,
        form=HorarioLaboralForm,
        extra=0, # Ponemos 1 para que pueda añadir nuevas reglas
        can_delete=True
    )

    # El queryset ahora filtra por el profesional
    queryset_horarios = HorarioLaboral.objects.filter(profesional=profesional_a_gestionar)
    
    if request.method == 'POST':
        if 'guardar_horarios' in request.POST:
            formset = HorarioFormSet(request.POST, queryset=queryset_horarios)
            if formset.is_valid():
                instances = formset.save(commit=False)
                for instance in instances:
                    instance.profesional = profesional_a_gestionar
                    instance.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                messages.success(request, "¡Tus reglas de horario han sido actualizadas correctamente!")
                return redirect('dashboard_horarios')
        elif 'crear_bloqueo' in request.POST:
            bloqueo_form = BloqueoForm(request.POST, prefix='bloqueo')
            if bloqueo_form.is_valid():
                nuevo_bloqueo = bloqueo_form.save(commit=False)
                nuevo_bloqueo.profesional = profesional_a_gestionar
                nuevo_bloqueo.save()
                messages.success(request, "¡Nuevo bloqueo creado exitosamente!")
                return redirect('dashboard_horarios')
    else:
        formset = HorarioFormSet(queryset=queryset_horarios)

    bloqueo_form = BloqueoForm(prefix='bloqueo')
    bloqueos_existentes = profesional_a_gestionar.dias_no_disponibles.filter(fecha_inicio__gte=timezone.localdate()).order_by('fecha_inicio')
    
    context = {
        'servicio_activo': servicio_activo,
        'profesional_gestionado': profesional_a_gestionar, # Pasamos el profesional para más claridad
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'formset': formset,
        'bloqueo_form': bloqueo_form,
        'bloqueos': bloqueos_existentes,
    }
    return render(request, 'dashboard_horarios.html', context)

@login_required
def dashboard_metricas(request):
    try:
        suscripcion = request.user.suscripcion
        tiene_acceso = suscripcion.is_active and suscripcion.plan.allow_metrics
    except (Suscripcion.DoesNotExist, AttributeError):
        tiene_acceso = False
    if not tiene_acceso and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Acceso denegado'}, status=403)
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_metricas.html', {'no_hay_servicio': True})
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True,
            'servicio_activo': servicio_activo,
            'tiene_acceso': tiene_acceso
        }
        return render(request, 'servicio_suspendido.html', context)
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
        else:
            año_str = request.GET.get('año', str(hoy.year))
            año = int(año_str)
            datos = qs.filter(fecha__year=año).annotate(periodo=TruncMonth('fecha')).values('periodo').annotate(total=Sum('ingreso_real')).order_by('periodo')
            labels = [d['periodo'].strftime('%b %Y') for d in datos]

        data_puntos = [float(d['total']) if d['total'] else 0 for d in datos]
        return JsonResponse({'labels': labels, 'data': data_puntos})
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
    else:
        fecha_inicio = hoy - timedelta(days=29)
        titulo_periodo = "Últimos 30 días"
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
        'tiene_acceso': tiene_acceso,
        'periodo_seleccionado': periodo,
    }
    return render(request, 'dashboard_metricas.html', context)

@login_required
def dashboard_servicios(request): # Apariencia
    try:
        suscripcion = request.user.suscripcion
        tiene_acceso = suscripcion.is_active and suscripcion.plan.allow_customization
    except (Suscripcion.DoesNotExist, AttributeError):
        tiene_acceso = False
    
    if not tiene_acceso and request.method == 'POST':
        messages.error(request, "Necesitas un plan activo para realizar esta acción.")
        return redirect('precios')
    
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo:
        return render(request, 'dashboard_servicios.html', {'no_hay_servicio': True})
    
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
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
    servicio_activo = get_servicio_activo(request)
    if not servicio_activo.esta_activo:
        context = {
            'servicio': servicio_activo,
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
        }
        return render(request, 'servicio_suspendido.html', context)
    if not servicio_activo:
        return render(request, 'dashboard_catalogo.html', {'no_hay_servicio': True})
    SubServicioFormSet = inlineformset_factory(
        Servicio, SubServicio,
        fields=('nombre', 'descripcion', 'duracion', 'precio'),
        extra=1, can_delete=True
    )
    if request.method == 'POST':
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
            'onboarding_completo': True,
            'servicio_activo': servicio_activo
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
    turnos_del_cliente = request.user.turnos_solicitados.all().select_related(
        'servicio', 'reseña'
    ).prefetch_related('sub_servicios_solicitados')
    
    ahora = timezone.now()
    hoy = ahora.date()
    hora_actual = ahora.time()
    turnos_futuros = turnos_del_cliente.filter(
        Q(fecha__gt=hoy) | Q(fecha=hoy, hora__gte=hora_actual)
    ).order_by('fecha', 'hora')

    turnos_pasados = turnos_del_cliente.filter(
        Q(fecha__lt=hoy) | Q(fecha=hoy, hora__lt=hora_actual)
    ).order_by('-fecha', '-hora')
    turnos_no_vistos_ids = list(turnos_del_cliente.filter(visto_por_cliente=False).values_list('id', flat=True))
    turnos_del_cliente.filter(id__in=turnos_no_vistos_ids).update(visto_por_cliente=True)
    context = {
        'turnos_futuros': turnos_futuros,
        'turnos_pasados': turnos_pasados,
        'turnos_no_vistos_ids': turnos_no_vistos_ids,
    }
    return render(request, 'mis_turnos.html', context)

@login_required
def confirmar_turno(request, turno_id):
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
                None,
                [turno.cliente.email],
                fail_silently=False,
            )
            messages.success(request, f"Turno confirmado y notificación enviada a {turno.cliente.first_name}.")
        except Exception as e:
            messages.error(request, f"El turno fue confirmado, pero hubo un error al enviar el email de notificación: {e}")
    return redirect('dashboard_propietario')

@login_required
def cancelar_turno(request, turno_id):
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
            instancia_turno.estado = 'completado'
            instancia_turno.save()
            if turno.ingreso_real is None:
                messages.success(request, f"¡Turno de {turno.cliente.username} finalizado con éxito!")
            else:
                messages.success(request, f"¡Ingreso del turno actualizado correctamente!")

            return redirect('dashboard_turnos')
    else:
        if turno.ingreso_real is not None:
            form = IngresoTurnoForm(instance=turno)
        else:
            precio_sugerido_dict = turno.sub_servicios_solicitados.aggregate(total=Sum('precio'))
            precio_sugerido = precio_sugerido_dict.get('total') or 0.00
            form = IngresoTurnoForm(instance=turno, initial={'ingreso_real': precio_sugerido})
    titulo_pagina = "Editar Ingreso del Turno" if turno.ingreso_real is not None else "Finalizar y Registrar Ingreso"
    context = {
        'form': form,
        'turno': turno,
        'servicio_activo': servicio_activo,
        'onboarding_completo': servicio_activo.configuracion_inicial_completa,
        'titulo_pagina': titulo_pagina,
    }
    return render(request, 'finalizar_turno.html', context)

@login_required
def obtener_notificaciones(request):
    if not request.user.is_authenticated:
        return JsonResponse({'conteo': 0})
    conteo_notificaciones = Turno.objects.filter(
        cliente=request.user, 
        estado__in=['confirmado', 'cancelado'],
        visto_por_cliente=False
    ).count()

    return JsonResponse({'conteo': conteo_notificaciones})

@login_required
def obtener_slots_disponibles(request, servicio_id):
    fecha_str = request.GET.get('fecha')
    duracion_str = request.GET.get('duracion')
    profesional_id_str = request.GET.get('profesional_id')
    
    if not all([fecha_str, duracion_str, profesional_id_str]):
        return JsonResponse({'error': 'Faltan parámetros.'}, status=400)

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        servicio = get_object_or_404(Servicio, id=servicio_id)
        duracion_requerida = int(duracion_str)
        profesional_id = int(profesional_id_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Parámetros inválidos.'}, status=400)
    
    try:
        profesional_a_consultar = Profesional.objects.get(id=profesional_id, servicio=servicio, activo=True)
    except Profesional.DoesNotExist:
        return JsonResponse({'slots': []})

    dia_de_la_semana_num = fecha.weekday()
    dia_map = {0: 'lunes', 1: 'martes', 2: 'miercoles', 3: 'jueves', 4: 'viernes', 5: 'sabado', 6: 'domingo'}
    nombre_dia_semana = dia_map.get(dia_de_la_semana_num)

    try:
        filtro_dia = {nombre_dia_semana: True}
        regla_horario = profesional_a_consultar.horarios.get(activo=True, **filtro_dia)
    except HorarioLaboral.DoesNotExist:
        return JsonResponse({'slots': []})
    except HorarioLaboral.MultipleObjectsReturned:
        regla_horario = profesional_a_consultar.horarios.filter(activo=True, **filtro_dia).first()

    turnos_del_dia = Turno.objects.filter(
        profesional=profesional_a_consultar, 
        fecha=fecha, 
        estado__in=['pendiente', 'confirmado']
    )
    bloqueos_del_dia = DiaNoDisponible.objects.filter(
        Q(profesional=profesional_a_consultar) & 
        (Q(fecha_inicio__lte=fecha, fecha_fin__gte=fecha) | Q(fecha_inicio=fecha, fecha_fin__isnull=True))
    )

    slots_disponibles = []
    duracion_requerida_td = timedelta(minutes=duracion_requerida)
    
    def generar_slots_en_periodo(hora_inicio_periodo, hora_fin_periodo):
        hora_actual_dt = datetime.combine(fecha, hora_inicio_periodo)
        hora_fin_dt = datetime.combine(fecha, hora_fin_periodo)
        if hora_actual_dt.minute % 15 != 0: hora_actual_dt += timedelta(minutes=(15 - (hora_actual_dt.minute % 15)))
        while hora_actual_dt + duracion_requerida_td <= hora_fin_dt:
            slot_inicio_dt, slot_fin_dt = hora_actual_dt, hora_actual_dt + duracion_requerida_td
            slot_esta_disponible = True
            for bloqueo in bloqueos_del_dia:
                if bloqueo.hora_inicio is None: slot_esta_disponible = False; break
                if slot_inicio_dt < datetime.combine(fecha, bloqueo.hora_fin) and slot_fin_dt > datetime.combine(fecha, bloqueo.hora_inicio): slot_esta_disponible = False; break
            if not slot_esta_disponible: hora_actual_dt += timedelta(minutes=15); continue
            for turno in turnos_del_dia:
                duracion_ocupacion = timedelta(minutes=(turno.duracion_total + servicio.duracion_buffer_minutos))
                if slot_inicio_dt < (datetime.combine(fecha, turno.hora) + duracion_ocupacion) and slot_fin_dt > datetime.combine(fecha, turno.hora): slot_esta_disponible = False; break
            if slot_esta_disponible: slots_disponibles.append(slot_inicio_dt.strftime('%H:%M'))
            hora_actual_dt += timedelta(minutes=15)

    periodos_de_trabajo = []
    apertura, cierre = regla_horario.horario_apertura, regla_horario.horario_cierre
    if regla_horario.tiene_descanso and regla_horario.descanso_inicio and regla_horario.descanso_fin:
        periodos_de_trabajo.append((apertura, regla_horario.descanso_inicio)); periodos_de_trabajo.append((regla_horario.descanso_fin, cierre))
    else: periodos_de_trabajo.append((apertura, cierre))
    for inicio, fin in periodos_de_trabajo:
        hora_inicio_busqueda = inicio
        if fecha == timezone.localdate():
            hora_minima_reserva = (timezone.localtime() + timedelta(minutes=15)).time()
            if hora_minima_reserva > hora_inicio_busqueda: hora_inicio_busqueda = hora_minima_reserva
        if hora_inicio_busqueda < fin: generar_slots_en_periodo(hora_inicio_busqueda, fin)

    return JsonResponse({'slots': sorted(list(set(slots_disponibles)))})

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '¡Tu perfil ha sido actualizado correctamente!')
            return redirect('editar_perfil')
    else:
        form = UserUpdateForm(instance=request.user)

    context = {
        'form': form
    }
    return render(request, 'editar_perfil.html', context)

@login_required
def toggle_favorito(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if servicio in request.user.servicios_favoritos.all():
        request.user.servicios_favoritos.remove(servicio)
    else:
        request.user.servicios_favoritos.add(servicio)
    
    return redirect(request.META.get('HTTP_REFERER', 'index'))

@login_required
def mis_favoritos(request):
    servicios_favoritos = request.user.servicios_favoritos.all()
    context = {
        'servicios': servicios_favoritos
    }
    return render(request, 'index.html', context)

def api_get_reseñas(request, servicio_slug):
    servicio = get_object_or_404(Servicio, slug=servicio_slug)
    calificacion_filtro = request.GET.get('calificacion')
    page_number = request.GET.get('page', 1)
    reseñas_list = servicio.reseñas.all().select_related('usuario').order_by('-fecha_creacion')
    if calificacion_filtro and calificacion_filtro.isdigit():
        reseñas_list = reseñas_list.filter(calificacion=int(calificacion_filtro))
    paginator = Paginator(reseñas_list, 4)
    page_obj = paginator.get_page(page_number)
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

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    success_url = reverse_lazy('index')
    redirect_authenticated_user = True

@login_required
def gestionar_equipo(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, propietario=request.user)
    tiene_acceso_prime = servicio.permite_multiples_profesionales
    
    profesionales = servicio.profesionales.all().order_by('nombre')
    
    context = {
        'servicio_activo': servicio,
        'servicio': servicio,
        'profesionales': profesionales,
        'tiene_acceso_prime': tiene_acceso_prime,
        'onboarding_completo': True,
    }
    return render(request, 'dashboard/gestionar_equipo.html', context)

@login_required
def crear_profesional(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id, propietario=request.user)
    if not servicio.permite_multiples_profesionales:
        messages.error(request, "Esta función requiere un plan Prime.")
        return redirect('dashboard_propietario')

    if request.method == 'POST':
        form = ProfesionalForm(request.POST, request.FILES, servicio=servicio)
        formset = HorarioLaboralFormSet(request.POST, prefix='horarios')

        if form.is_valid() and formset.is_valid():
            profesional = form.save(commit=False)
            profesional.servicio = servicio
            profesional.save()
            
            formset.instance = profesional
            formset.save()
            
            horarios_creados = profesional.horarios.all()
            horario_valido_encontrado = None
            
            for horario in horarios_creados:
                dias_seleccionados = (
                    horario.lunes or horario.martes or horario.miercoles or
                    horario.jueves or horario.viernes or horario.sabado or horario.domingo
                )
                if not dias_seleccionados or not horario.horario_apertura:
                    horario.delete() 
                else:
                    horario_valido_encontrado = horario
            
            if horario_valido_encontrado and not horario_valido_encontrado.activo:
                horario_valido_encontrado.activo = True
                horario_valido_encontrado.save()
            
            messages.success(request, f"¡{profesional.nombre} y su horario han sido creados correctamente!")
            return redirect('gestionar_equipo', servicio_id=servicio.id)
        else:
            messages.error(request, "Hubo un error en el formulario. Por favor, revisa los datos.")

    else:
        form = ProfesionalForm(servicio=servicio)
        formset = HorarioLaboralFormSet(queryset=HorarioLaboral.objects.none(), prefix='horarios')

    context = {
        'form': form,
        'formset': formset,
        'servicio': servicio,
        'servicio_activo': servicio,
        'onboarding_completo': True,
        'form_title': "Añadir Nuevo Miembro"
    }
    return render(request, 'dashboard/crear_editar_profesional.html', context)

@login_required
def editar_profesional(request, profesional_id):
    profesional = get_object_or_404(Profesional, id=profesional_id, servicio__propietario=request.user)
    servicio = profesional.servicio

    if request.method == 'POST':
        form = ProfesionalForm(request.POST, request.FILES, instance=profesional, servicio=servicio)
        # ¡USAMOS EL FORMSET REAL!
        formset = HorarioLaboralFormSet(request.POST, instance=profesional)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f"Los datos y el horario de {profesional.nombre} han sido actualizados.")
            return redirect('gestionar_equipo', servicio_id=servicio.id)
    else:
        form = ProfesionalForm(instance=profesional, servicio=servicio)
        # ¡USAMOS EL FORMSET REAL!
        formset = HorarioLaboralFormSet(instance=profesional)

    context = {
        'form': form,
        'formset': formset,
        'profesional': profesional,
        'servicio': servicio,
        # Variables extra para que la plantilla base no falle
        'servicio_activo': servicio,
        'onboarding_completo': True,
        'form_title': f"Editando a {profesional.nombre}"
    }
    return render(request, 'dashboard/crear_editar_profesional.html', context)

# VISTA 3: Lógica para ELIMINAR un profesional (se llama desde un botón)
@login_required
@require_POST # Para más seguridad, esta acción solo se permite via POST
def eliminar_profesional(request, profesional_id):
    profesional = get_object_or_404(Profesional, id=profesional_id, servicio__propietario=request.user)
    servicio_id = profesional.servicio.id
    
    # Lógica de seguridad: No permitir borrar el último profesional
    if profesional.servicio.profesionales.count() <= 1:
        messages.error(request, "No puedes eliminar al último miembro del equipo. Un servicio debe tener al menos un profesional.")
        return redirect('gestionar_equipo', servicio_id=servicio_id)

    nombre_profesional = profesional.nombre
    profesional.delete()
    messages.success(request, f"{nombre_profesional} ha sido eliminado del equipo.")
    return redirect('gestionar_equipo', servicio_id=servicio_id)

@login_required
def obtener_notificaciones_propietario(request):
    if not request.user.is_authenticated or not request.user.servicios_propios.exists():
        return JsonResponse({'conteo': 0})

    total_pendientes = 0
    servicios_del_propietario = request.user.servicios_propios.all()
    
    for servicio in servicios_del_propietario:
        total_pendientes += Turno.objects.filter(servicio=servicio, estado='pendiente').count()

    return JsonResponse({'conteo': total_pendientes})

def get_horario_profesional_api(request, profesional_id):
    try:
        profesional = get_object_or_404(Profesional, id=profesional_id)
        horarios_activos = profesional.horarios.filter(activo=True)
        
        dias_laborables = set()
        dias_map = {
            'lunes': 1, 'martes': 2, 'miercoles': 3, 'jueves': 4,
            'viernes': 5, 'sabado': 6, 'domingo': 0
        }

        for horario in horarios_activos:
            for dia_nombre, dia_numero in dias_map.items():
                if getattr(horario, dia_nombre):
                    dias_laborables.add(dia_numero)
                    
        return JsonResponse({'dias_laborables': list(dias_laborables)})

    except Profesional.DoesNotExist:
        return JsonResponse({'error': 'Profesional no encontrado'}, status=404)