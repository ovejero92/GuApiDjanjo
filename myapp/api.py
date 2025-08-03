from rest_framework import viewsets, permissions
from .models import Servicio, Turno
from .serializers import ServicioSerializer, TurnoSerializer

class ServicioViewSet(viewsets.ModelViewSet):
    queryset = Servicio.objects.all()
    serializer_class = ServicioSerializer
    permission_classes = [permissions.DjangoModelPermissionsOrAnonReadOnly]

class TurnoViewSet(viewsets.ModelViewSet):
    queryset = Turno.objects.all()
    serializer_class = TurnoSerializer
    
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(cliente=self.request.user)
