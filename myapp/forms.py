from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Turno

class TurnoForm(forms.ModelForm):
    class Meta:
        model = Turno
        fields = ['fecha', 'hora']  # no necesitamos mostrar servicio al usuario
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, servicio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.servicio = servicio

    def clean(self):
        cleaned_data = super().clean()
        hora = cleaned_data.get('hora')
        if self.servicio and hora:
            apertura = self.servicio.horario_apertura
            cierre = self.servicio.horario_cierre
            if hora < apertura or hora > cierre:
                raise forms.ValidationError(
                    f"El servicio '{self.servicio.nombre}' atiende entre {apertura.strftime('%H:%M')} y {cierre.strftime('%H:%M')}."
                )
        return cleaned_data

    def save(self, commit=True):
        turno = super().save(commit=False)
        turno.servicio = self.servicio
        if commit:
            turno.save()
        return turno

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')