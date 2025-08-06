from django import forms
from django.contrib.auth.models import User
from .models import Turno,Profesional , HorarioLaboral, DiaNoDisponible, Reseña, Servicio, SubServicio, MedioDePago
from django.utils.text import slugify
from PIL import Image
from django.shortcuts import  get_object_or_404
from django.forms import inlineformset_factory


class CustomImageWidget(forms.widgets.ClearableFileInput):
    template_name = 'widgets/mi_widget_de_imagen.html'

class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label="Tu Nombre", required=True)
    telefono = forms.CharField(max_length=25, label="Teléfono", required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        telefono_ingresado = self.cleaned_data.get('telefono')

        user.save()

        if telefono_ingresado:
            user.perfil.telefono = telefono_ingresado
            user.perfil.save()
        
        return user

class CustomSocialSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label="Tu Nombre", required=True)

    def signup(self, request, sociallogin):

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
    medio_de_pago = forms.ChoiceField(
        label="¿Cómo deseas pagar?",
        required=True
    )
    profesional = forms.ModelChoiceField(
        queryset=Profesional.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )
    class Meta:
        model = Turno
        fields = ['fecha', 'hora', 'sub_servicios_solicitados', 'medio_de_pago', 'profesional']
        widgets = {
            'fecha': forms.TextInput(attrs={'placeholder': 'dd/mm/aaaa', 'readonly': 'readonly'}),
            'hora': forms.HiddenInput(),
        }
    def __init__(self, *args, **kwargs):
        servicio = kwargs.pop('servicio', None)
        super().__init__(*args, **kwargs)

        if servicio:
            self.fields['sub_servicios_solicitados'].queryset = SubServicio.objects.filter(servicio_padre=servicio)
            opciones_pago = [(mdp.slug, mdp.nombre_visible) for mdp in servicio.medios_de_pago_aceptados.all()]
            self.fields['medio_de_pago'].choices = opciones_pago
            
            if servicio.permite_multiples_profesionales:
                self.fields['profesional'].queryset = Profesional.objects.filter(servicio=servicio, activo=True)

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
        return cleaned_data

    def save(self, commit=True):
        turno = super().save(commit=False)
        turno.duracion_total = self.cleaned_data['duracion_total']
        turno.medio_de_pago = self.cleaned_data['medio_de_pago']
        turno.servicio = self.cleaned_data['sub_servicios_solicitados'].first().servicio_padre
        if commit:
            turno.save()
            self.save_m2m()
        return turno

class IngresoTurnoForm(forms.ModelForm):
    medio_de_pago_final = forms.ChoiceField(
        label="Método de Pago Final",
        required=True
    )

    class Meta:
        model = Turno
        fields = ['ingreso_real']
        labels = {
            'ingreso_real': 'Monto Final Cobrado ($)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        turno = self.instance
        if turno and turno.servicio:
            opciones = [
                (mdp.slug, mdp.nombre_visible) 
                for mdp in turno.servicio.medios_de_pago_aceptados.all()
            ]
            self.fields['medio_de_pago_final'].choices = opciones
            self.fields['medio_de_pago_final'].initial = turno.medio_de_pago_final or turno.medio_de_pago
            
        self.fields['ingreso_real'].required = True

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        instance.medio_de_pago_final = self.cleaned_data.get('medio_de_pago_final')
        
        if commit:
            instance.save()
            
        return instance

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(label="Correo Electrónico", required=True)
    telefono = forms.CharField(label="Teléfono", max_length=25, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if self.instance and hasattr(self.instance, 'perfil'):
            self.fields['telefono'].initial = self.instance.perfil.telefono

    def save(self, commit=True):
        user = super().save(commit=commit)
        
        if hasattr(user, 'perfil'):
            user.perfil.telefono = self.cleaned_data.get('telefono')
            if commit:
                user.perfil.save()
                
        return user
    
class ReseñaForm(forms.ModelForm):
    class Meta:
        model = Reseña
        fields = ['calificacion', 'comentario']
        widgets = {
            'calificacion': forms.RadioSelect(
                choices=[(i, str(i)) for i in range(1, 6)]
            ),
            'comentario': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'calificacion': 'Tu Calificación:',
            'comentario': 'Tu Comentario (opcional)',
        }

class ServicioPersonalizacionForm(forms.ModelForm):
    def save(self, commit=True):

        try:
            original_instance = Servicio.objects.get(pk=self.instance.pk)
            original_banner = original_instance.imagen_banner
        except Servicio.DoesNotExist:
            original_banner = None

        new_instance = super().save(commit=False)

        if original_banner and original_banner != new_instance.imagen_banner:

            original_banner.delete(save=False)

        if commit:
            new_instance.save()
            
        return new_instance

    def clean_slug(self):
        slug_ingresado = self.cleaned_data.get('slug')
        slug_limpio = slugify(slug_ingresado)

        if Servicio.objects.filter(slug=slug_limpio).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("¡Oh no! Esta URL ya está en uso. Por favor, elige otra.")
        
        return slug_limpio
    
    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        
        if not logo:
            return logo

        try:
            image = Image.open(logo)
            width, height = image.size

            if abs(width - height) / width > 0.05:
                raise forms.ValidationError("La imagen del logo debe ser cuadrada (ej: 400x400px).")

            if width < 200 or height < 200:
                raise forms.ValidationError("La imagen del logo es demasiado pequeña. Debe ser de al menos 200x200px.")

        except Exception as e:
            raise forms.ValidationError(f"No se pudo procesar el archivo. Asegúrate de que sea una imagen válida. Error: {e}")

        return logo

    class Meta:
        model = Servicio
        fields = [
            'logo','color_primario', 'color_fondo', 'color_texto' , 'imagen_banner',
            'fuente_titulos', 'fuente_cuerpo', 'slug',
            'footer_direccion', 'footer_telefono', 'footer_email',
            'footer_instagram_url', 'footer_facebook_url', 'footer_tiktok_url',
            'color_slot', 'color_slot_seleccionado'
        ]
        widgets = {
            'color_primario': forms.TextInput(attrs={'type': 'color'}),
            'color_fondo': forms.TextInput(attrs={'type': 'color'}),
            'color_texto': forms.TextInput(attrs={'type': 'color'}),
            'color_slot': forms.TextInput(attrs={'type': 'color'}),
            'color_slot_seleccionado': forms.TextInput(attrs={'type': 'color'}),
            'fuente_titulos': forms.Select(attrs={'class': 'form-control'}),
            'fuente_cuerpo': forms.Select(attrs={'class': 'form-control'}),
            'footer_direccion': forms.TextInput(attrs={'placeholder': 'Ej: Av. Siempreviva 742'}),
            'footer_telefono': forms.TextInput(attrs={'placeholder': 'Ej: +54 9 11 1234-5678'}),
            'footer_email': forms.EmailInput(attrs={'placeholder': 'Ej: contacto@minegocio.com'}),
            'footer_instagram_url': forms.TextInput(attrs={'placeholder': 'tu-usuario'}),
            'footer_facebook_url': forms.TextInput(attrs={'placeholder': 'tu-usuario'}),
            'footer_tiktok_url': forms.TextInput(attrs={'placeholder': '@tu.usuario'}),
        }
        help_texts = {
            'slug': "Esta será la URL de tu negocio. Usa solo letras, números y guiones. Sin espacios."
        }

class ServicioUpdateForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'descripcion', 'direccion', 'categoria', 'medios_de_pago_aceptados', 'duracion_buffer_minutos']
        labels = {
            'nombre': 'Nombre del Negocio',
            'descripcion': 'Descripción corta',
            'direccion': 'Dirección',
            'categoria': 'Categoría de tu Negocio',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
        }

class ServicioCreateForm(forms.ModelForm):
    class Meta:
        model = Servicio
        fields = ['nombre', 'categoria', 'descripcion', 'direccion', 'medios_de_pago_aceptados', 'duracion_buffer_minutos']
        labels = {
            'nombre': '¿Cómo se llama tu negocio?',
            'categoria': '¿A qué categoría pertenece?',
            'descripcion': 'Describe brevemente tu servicio',
            'direccion': 'Dirección de tu negocio',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

class BloqueoForm(forms.ModelForm):
    class Meta:
        model = DiaNoDisponible
        fields = ['fecha_inicio', 'fecha_fin', 'hora_inicio', 'hora_fin', 'motivo']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}),
        }
        labels = {
            'fecha_inicio': 'Fecha de Inicio (o día único)',
            'fecha_fin': 'Fecha de Fin (opcional, para rangos)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        inicio = cleaned_data.get("hora_inicio")
        fin = cleaned_data.get("hora_fin")

        if (inicio and not fin) or (fin and not inicio):
            raise forms.ValidationError("Debe especificar tanto la hora de inicio como la de fin para un bloqueo parcial.")
        if inicio and fin and inicio >= fin:
            raise forms.ValidationError("La hora de inicio debe ser anterior a la hora de fin.")
        
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError("La fecha de fin no puede ser anterior a la de inicio.")

        return cleaned_data
    
class HorarioLaboralForm(forms.ModelForm):
    dias_semana = forms.MultipleChoiceField(
        choices=[('lunes', 'Lunes'), ('martes', 'Martes'), ('miercoles', 'Miércoles'), ('jueves', 'Jueves'), ('viernes', 'Viernes'), ('sabado', 'Sábado'), ('domingo', 'Domingo')],
        widget=forms.CheckboxSelectMultiple,
        label="Días de la semana para esta regla",
        required=False
    )
    
    class Meta:
        model = HorarioLaboral
        exclude = ['servicio', 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        widgets = {
            'horario_apertura': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_cierre': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descanso_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descanso_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            # ...
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        dias_seleccionados = self.cleaned_data.get('dias_semana', [])
        
        instance.lunes = False
        instance.martes = False
        instance.miercoles = False
        instance.jueves = False
        instance.viernes = False
        instance.sabado = False
        instance.domingo = False

        for dia in dias_seleccionados:
            if hasattr(instance, dia):
                setattr(instance, dia, True)

        if commit:
            instance.save()
            
        return instance
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            dias_iniciales = []
            if self.instance.lunes: dias_iniciales.append('lunes')
            if self.instance.martes: dias_iniciales.append('martes')
            if self.instance.miercoles: dias_iniciales.append('miercoles')
            if self.instance.jueves: dias_iniciales.append('jueves')
            if self.instance.viernes: dias_iniciales.append('viernes')
            if self.instance.sabado: dias_iniciales.append('sabado')
            if self.instance.domingo: dias_iniciales.append('domingo')
            
            self.fields['dias_semana'].initial = dias_iniciales

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('dias_semana'):
            self.add_error('dias_semana', 'Debes seleccionar al menos un día para esta regla.')
        return cleaned_data
    
class ProfesionalHorarioForm(forms.ModelForm):
    # Definimos los días como un campo de checkboxes múltiples para tener el control.
    dias_semana = forms.MultipleChoiceField(
        choices=[('lunes', 'Lunes'), ('martes', 'Martes'), ('miercoles', 'Miércoles'), ('jueves', 'Jueves'), ('viernes', 'Viernes'), ('sabado', 'Sábado'), ('domingo', 'Domingo')],
        widget=forms.CheckboxSelectMultiple, # Lo renderizaremos a mano en la plantilla.
        label="Días de la semana para esta regla:",
        required=False
    )
    
    class Meta:
        model = HorarioLaboral
        # Excluimos los campos booleanos individuales porque usaremos 'dias_semana'
        exclude = ['profesional', 'servicio', 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        widgets = {
            'horario_apertura': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_cierre': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descanso_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descanso_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'tiene_descanso': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # Esta lógica es crucial: lee los campos booleanos del modelo (lunes, martes...)
    # y los usa para pre-seleccionar los checkboxes en 'dias_semana'.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            dias_iniciales = []
            for dia in ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']:
                if getattr(self.instance, dia, False):
                    dias_iniciales.append(dia)
            self.fields['dias_semana'].initial = dias_iniciales

    # Esta lógica es la inversa: toma los checkboxes seleccionados
    # y actualiza los campos booleanos del modelo antes de guardar.
    def save(self, commit=True):
        instance = super().save(commit=False)
        dias_seleccionados = self.cleaned_data.get('dias_semana', [])
        
        for dia in ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']:
            setattr(instance, dia, dia in dias_seleccionados)

        if commit:
            instance.save()
            
        return instance

# 2. Ahora le decimos al inlineformset_factory que use NUESTRO formulario personalizado.
HorarioLaboralFormSet = inlineformset_factory(
    Profesional,
    HorarioLaboral,
    form=ProfesionalHorarioForm,  # ¡LA LÍNEA MÁGICA!
    extra=1,
    max_num=1,
    can_delete=False,
)


class ProfesionalForm(forms.ModelForm):
    sub_servicios_ofrecidos = forms.ModelMultipleChoiceField(
        queryset=SubServicio.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Sub servicios ofrecidos"
    )
    class Meta:
        model = Profesional
        fields = ['nombre', 'email', 'sub_servicios_ofrecidos']
        labels = {
            'nombre': 'Nombre:',
            'email': 'Email (opcional):'
        }
        help_texts = {
            'nombre': "Nombre del miembro del equipo, ej: 'Dra. Ana Pérez' o 'Estilista Juan'",
            'email': "Email opcional para notificaciones internas.",
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Dra. Ana Pérez'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email (opcional)'}),
        }
    
    def __init__(self, *args, **kwargs):
        servicio = kwargs.pop('servicio', None)
        super().__init__(*args, **kwargs)

        if servicio:
            self.fields['sub_servicios_ofrecidos'].queryset = servicio.sub_servicios.all()
        
        self.fields['email'].required = False