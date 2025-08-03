from django import forms
from django.contrib.auth.models import User
from .models import Turno, HorarioLaboral, DiaNoDisponible, Reseña, Servicio, SubServicio, MedioDePago
from django.utils.text import slugify
from django.shortcuts import  get_object_or_404


class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=30, label="Tu Nombre", required=True)
    telefono = forms.CharField(max_length=25, label="Teléfono", required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data['first_name']
        telefono_ingresado = self.cleaned_data.get('telefono')

        # 2. Guardamos el nombre en el modelo User principal.
        user.save()

        if telefono_ingresado:
            user.perfil.telefono = telefono_ingresado
            user.perfil.save()
        
        # 4. Devolvemos el usuario. allauth se encarga del resto.
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
    medio_de_pago = forms.ChoiceField(
        label="¿Cómo deseas pagar?",
        required=True
    )
    class Meta:
        model = Turno
        fields = ['fecha', 'hora', 'medio_de_pago']
        widgets = {
            'fecha': forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
        }
    def __init__(self, *args, servicio_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if servicio_id:
            servicio = get_object_or_404(Servicio, id=servicio_id)
            self.fields['sub_servicios_solicitados'].queryset = SubServicio.objects.filter(servicio_padre_id=servicio_id)
            opciones_disponibles = [
                (mdp.slug, mdp.nombre_visible) 
                for mdp in servicio.medios_de_pago_aceptados.all()
            ]
            # 3. Asignamos esas opciones al campo 'medio_de_pago'
            self.fields['medio_de_pago'].choices = opciones_disponibles

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
            'footer_instagram_url': forms.URLInput(attrs={'placeholder': 'https://instagram.com/tu-usuario'}),
            'footer_facebook_url': forms.URLInput(attrs={'placeholder': 'https://facebook.com/tu-pagina'}),
            'footer_tiktok_url': forms.URLInput(attrs={'placeholder': 'https://tiktok.com/@tu.usuario'}),
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
        # 2. Añadimos el nuevo campo a la lista de campos que se mostrarán.
        #    También podemos añadir la dirección aquí si tiene sentido en tu flujo.
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

        # Tu lógica de validación se queda igual, pero la copio para que esté completa
        if (inicio and not fin) or (fin and not inicio):
            raise forms.ValidationError("Debe especificar tanto la hora de inicio como la de fin para un bloqueo parcial.")
        if inicio and fin and inicio >= fin:
            raise forms.ValidationError("La hora de inicio debe ser anterior a la hora de fin.")
        
        # Validación extra que faltaba en el modelo
        fecha_inicio = cleaned_data.get("fecha_inicio")
        fecha_fin = cleaned_data.get("fecha_fin")
        if fecha_fin and fecha_fin < fecha_inicio:
            raise forms.ValidationError("La fecha de fin no puede ser anterior a la de inicio.")

        return cleaned_data
    
class HorarioLaboralForm(forms.ModelForm):
    # Usamos MultipleChoiceField para mostrar los checkboxes
    dias_semana = forms.MultipleChoiceField(
        # Las opciones ahora se definen aquí, en el formulario
        choices=[('lunes', 'Lunes'), ('martes', 'Martes'), ('miercoles', 'Miércoles'), ('jueves', 'Jueves'), ('viernes', 'Viernes'), ('sabado', 'Sábado'), ('domingo', 'Domingo')],
        widget=forms.CheckboxSelectMultiple,
        label="Días de la semana para esta regla",
        required=False # Lo hacemos no requerido a nivel de form, luego validamos
    )
    
    class Meta:
        model = HorarioLaboral
        # Excluimos los campos de día individuales porque los manejaremos nosotros
        exclude = ['servicio', 'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        widgets = {
            'horario_apertura': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'horario_cierre': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descanso_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'descanso_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            # ...
        }

    # --- INICIO DE LA CORRECCIÓN DEL MÉTODO save ---
    def save(self, commit=True):
        # 1. Obtenemos la instancia del modelo, pero todavía no la guardamos en la DB
        instance = super().save(commit=False)
        
        # 2. Obtenemos la lista de días que el usuario marcó en los checkboxes
        dias_seleccionados = self.cleaned_data.get('dias_semana', [])
        
        # 3. Reiniciamos todos los campos de día a False. Esto es importante
        #    para cuando el usuario edita una regla y desmarca un día.
        instance.lunes = False
        instance.martes = False
        instance.miercoles = False
        instance.jueves = False
        instance.viernes = False
        instance.sabado = False
        instance.domingo = False

        # 4. Recorremos la lista de días seleccionados y ponemos a True los campos correspondientes.
        for dia in dias_seleccionados:
            # setattr(instance, 'lunes', True) es lo mismo que instance.lunes = True
            if hasattr(instance, dia):
                setattr(instance, dia, True)

        # 5. Si commit es True, ahora sí guardamos la instancia completa en la base de datos.
        if commit:
            instance.save()
            
        return instance
    # --- FIN DE LA CORRECCIÓN DEL MÉTODO save ---

    # --- INICIO DE LA LÓGICA DE RELLENADO (para la edición) ---
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando una regla existente...
        if self.instance and self.instance.pk:
            # ...leemos los valores booleanos del modelo...
            dias_iniciales = []
            if self.instance.lunes: dias_iniciales.append('lunes')
            if self.instance.martes: dias_iniciales.append('martes')
            if self.instance.miercoles: dias_iniciales.append('miercoles')
            if self.instance.jueves: dias_iniciales.append('jueves')
            if self.instance.viernes: dias_iniciales.append('viernes')
            if self.instance.sabado: dias_iniciales.append('sabado')
            if self.instance.domingo: dias_iniciales.append('domingo')
            
            # ...y los usamos para marcar los checkboxes correspondientes.
            self.fields['dias_semana'].initial = dias_iniciales
    # --- FIN DE LA LÓGICA DE RELLENADO ---

    def clean(self):
        cleaned_data = super().clean()
        # Validación para asegurar que al menos un día sea seleccionado
        if not cleaned_data.get('dias_semana'):
            self.add_error('dias_semana', 'Debes seleccionar al menos un día para esta regla.')
        return cleaned_data