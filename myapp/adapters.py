from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

class MyAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        """
        Controla a dónde va el usuario después de iniciar sesión o registrarse.
        """
        # Primero, revisamos si la URL tiene una instrucción 'next'.
        next_url = request.GET.get('next')
        if next_url:
            # Si la tiene, ¡la obedecemos!
            return next_url

        # Si no hay 'next', aplicamos nuestra propia lógica.
        # ¿El usuario que acaba de iniciar sesión es un propietario?
        if request.user.servicios_propios.exists():
            # Si sí, lo mandamos a su dashboard.
            path = reverse('dashboard_propietario')
        else:
            # Si no, es un cliente normal. Lo mandamos al inicio.
            # O podríamos mandarlo a 'mis_turnos', ¡tú decides!
            path = reverse('index')
        
        return path