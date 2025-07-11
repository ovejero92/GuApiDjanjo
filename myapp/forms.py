from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Turno, HorarioLaboral, DiaNoDisponible, Reseña
from django.utils import timezone
from datetime import datetime, timedelta

class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label="Tu Nombre", required=True)

    # allauth añadirá automáticamente los campos de email, password y password2.
    # Nosotros solo añadimos los campos "extra".

    def signup(self, request, user):
        """
        Guarda los datos extra (el nombre) en el objeto de usuario.
        """
        user.first_name = self.cleaned_data['first_name']
        user.save()
        return user

# ==============================================================================
# FORMULARIO PARA EL REGISTRO SOCIAL (CON GOOGLE)
# ==============================================================================
# Este es el que se mostrará DESPUÉS de hacer login con Google por primera vez.
class CustomSocialSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label="Tu Nombre", required=True)

    def signup(self, request, sociallogin):
        """
        Guarda los datos extra en el objeto de usuario que viene del login social.
        """
        user = sociallogin.user
        user.first_name = self.cleaned_data['first_name']
        user.save()
        return user

class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['fecha', 'hora']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, servicio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.servicio = servicio

    def clean(self):
        # Esta lógica de validación está perfecta, no necesita cambios.
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        servicio = self.servicio

        if not (fecha and hora and servicio):
            return cleaned_data

        fecha_hora_turno = timezone.make_aware(datetime.combine(fecha, hora))
        if fecha_hora_turno < timezone.now():
            raise forms.ValidationError("No puedes solicitar un turno en una fecha u hora que ya ha pasado.")

        dia_semana = fecha.weekday()
        try:
            horario_del_dia = servicio.horarios.get(dia_semana=dia_semana, activo=True)
            apertura = horario_del_dia.horario_apertura
            cierre = horario_del_dia.horario_cierre
        except HorarioLaboral.DoesNotExist:
            raise forms.ValidationError(f"El negocio no opera los días {fecha.strftime('%A')}.")
        
        duracion_servicio = timedelta(minutes=servicio.duracion)
        hora_fin_turno_nuevo = (datetime.combine(datetime.min, hora) + duracion_servicio).time()

        if not (apertura <= hora < cierre and apertura <= hora_fin_turno_nuevo <= cierre):
             raise forms.ValidationError(
                f"El horario del turno debe estar completamente dentro del horario de atención de este día ({apertura.strftime('%H:%M')} - {cierre.strftime('%H:%M')})."
            )

        bloqueos = servicio.dias_no_disponibles.filter(fecha=fecha)
        for bloqueo in bloqueos:
            if bloqueo.hora_inicio is None and bloqueo.hora_fin is None:
                raise forms.ValidationError(f"El día {fecha.strftime('%d/%m/%Y')} no está disponible por: {bloqueo.motivo or 'motivos internos'}.")
            
            if bloqueo.hora_inicio and bloqueo.hora_fin:
                if hora < bloqueo.hora_fin and hora_fin_turno_nuevo > bloqueo.hora_inicio:
                    raise forms.ValidationError(
                        f"El horario seleccionado no está disponible por un bloqueo de {bloqueo.hora_inicio.strftime('%H:%M')} a {bloqueo.hora_fin.strftime('%H:%M')}."
                    )

        turnos_existentes = Turno.objects.filter(servicio=servicio, fecha=fecha)
        for turno_existente in turnos_existentes:
            hora_inicio_existente = turno_existente.hora
            duracion_existente = timedelta(minutes=turno_existente.servicio.duracion)
            hora_fin_existente = (datetime.combine(datetime.min, hora_inicio_existente) + duracion_existente).time()

            if hora < hora_fin_existente and hora_fin_turno_nuevo > hora_inicio_existente:
                raise forms.ValidationError(
                    f"El horario de {hora.strftime('%H:%M')} a {hora_fin_turno_nuevo.strftime('%H:%M')} se superpone con un turno ya existente."
                )

        return cleaned_data

    def save(self, commit=True):
        turno = super().save(commit=False)
        turno.servicio = self.servicio
        if commit:
            turno.save()
        return turno

class IngresoTurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['ingreso_real']
        labels = {
            'ingreso_real': 'Monto Final Cobrado ($)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ingreso_real'].required = True

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

class ReseñaForm(forms.ModelForm):
    class Meta:
        model = Reseña
        fields = ['calificacion', 'comentario']
        widgets = {
            'calificacion': forms.NumberInput(attrs={
                'type': 'range', 'min': '1', 'max': '5', 'step': '1',
                'class': 'rating-slider'
            }),
            'comentario': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'calificacion': 'Tu Calificación (1 a 5 estrellas)',
            'comentario': 'Tu Comentario (opcional)',
        }

class BloqueoForm(forms.ModelForm):
    class Meta:
        model = DiaNoDisponible
        fields = ['fecha', 'hora_inicio', 'hora_fin', 'motivo']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("hora_inicio")
        fin = cleaned_data.get("hora_fin")
        if (inicio and not fin) or (fin and not inicio):
            raise forms.ValidationError("Debe especificar tanto la hora de inicio como la de fin para un bloqueo parcial.")
        if inicio and fin and inicio >= fin:
            raise forms.ValidationError("La hora de inicio debe ser anterior a la hora de fin.")
        return cleaned_data