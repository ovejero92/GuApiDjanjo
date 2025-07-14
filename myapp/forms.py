from django import forms
from django.contrib.auth.models import User
from .models import Turno, HorarioLaboral, DiaNoDisponible, Reseña, Servicio, SubServicio
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
    sub_servicios_solicitados = forms.ModelMultipleChoiceField(
        queryset=SubServicio.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label="Selecciona los servicios que deseas",
        required=True
    )
    class Meta:
        model = Turno
        fields = ['fecha', 'hora']
        widgets = {
            'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
        }
    def __init__(self, *args, servicio_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if servicio_id:
            self.fields['sub_servicios_solicitados'].queryset = SubServicio.objects.filter(servicio_padre_id=servicio_id)

    def clean(self):
        cleaned_data = super().clean()
        sub_servicios_seleccionados = cleaned_data.get('sub_servicios_solicitados')
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        if not (sub_servicios_seleccionados and fecha and hora):
            return cleaned_data
        servicio_padre = sub_servicios_seleccionados.first().servicio_padre
        duracion_total_minutos = sum(sub.duracion for sub in sub_servicios_seleccionados)
        self.cleaned_data['duracion_total'] = duracion_total_minutos
        # Aquí puedes añadir la lógica de validación completa si lo deseas
        return cleaned_data

    def save(self, commit=True):
        turno = super().save(commit=False)
        turno.duracion_total = self.cleaned_data['duracion_total']
        turno.servicio = self.cleaned_data['sub_servicios_solicitados'].first().servicio_padre
        if commit:
            turno.save()
            self.save_m2m()
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

class ServicioPersonalizacionForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['color_primario', 'color_fondo', 'imagen_banner', 'footer_personalizado']
        widgets = {
            'color_primario': forms.TextInput(attrs={'type': 'color'}),
            'color_fondo': forms.TextInput(attrs={'type': 'color'}),
        }

class ServicioUpdateForm(forms.ModelForm):
    class Meta:
        model = Servicio
        # ========== INICIO DE LA CORRECCIÓN ==========
        # Reemplazamos 'direccion_texto' por 'direccion', que es el nombre real de tu campo.
        fields = ['nombre', 'descripcion', 'direccion']
        # ========== FIN DE LA CORRECCIÓN ==========
        labels = {
            'nombre': 'Nombre del Negocio',
            'descripcion': 'Descripción corta',
            'direccion': 'Dirección', # Corregimos la etiqueta también
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
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