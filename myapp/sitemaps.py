from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Servicio

class StaticViewSitemap(Sitemap):
    def items(self):
        return ['index', 'about', 'precios', 'terminos', 'privacidad']

    def location(self, item):
        return reverse(item)

class ServicioSitemap(Sitemap):
    def items(self):
        return Servicio.objects.filter(esta_activo=True)

    def lastmod(self, obj):
        # Asumiendo que tienes un campo de última modificación, si no, puedes quitar esta línea.
        # return obj.fecha_actualizacion 
        return None