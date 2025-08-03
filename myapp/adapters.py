from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse

class MyAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        next_url = request.GET.get('next')
        if next_url:
            return next_url

        if request.user.servicios_propios.exists():
            path = reverse('dashboard_propietario')
        else:
            path = reverse('index')
        
        return path