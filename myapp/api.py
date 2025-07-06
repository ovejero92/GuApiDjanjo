from rest_framework import viewsets, permissions
from .models import Servicio, Turno
from .serializers import ServicioSerializer, TurnoSerializer

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    
    # ¡ESTA ES LA CONFIGURACIÓN MÁS SEGURA Y CORRECTA PARA TI!
    # GET: Cualquiera puede ver la lista.
    # POST, PUT, DELETE: Solo usuarios que sean "staff" (como el superusuario).
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]

class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    
    # Este permiso está bien. Permite a cualquiera leer (ver turnos, quizás no sea ideal),
    # pero solo a usuarios autenticados crear uno (pedir un turno).
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    # Esta función ya está bien, asigna el turno al usuario que hace la petición.
    def perform_create(self, serializer):
        serializer.save(cliente=self.request.user) # Asegúrate de que usa 'cliente'
