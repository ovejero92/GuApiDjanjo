from rest_framework import serializers
from .models import Servicio, Turno
from django.contrib.auth.models import User

class ServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servicio
        fields = '__all__'

class TurnoSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = Turno
        fields = ['id', 'usuario', 'usuario_username', 'servicio', 'fecha', 'hora', 'estado']