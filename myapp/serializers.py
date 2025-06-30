from rest_framework import serializers
from .models import Servicio, Turno
from django.contrib.auth.models import User

class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = '__all__'

class TurnoSerializer(serializers.ModelSerializer):
    cliente_username = serializers.CharField(source='cliente.username', read_only=True)

    class Meta:
        model = Turno
        fields = ['id', 'cliente', 'cliente_username', 'servicio', 'fecha', 'hora', 'estado']
