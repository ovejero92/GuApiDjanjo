from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login
from .models import Servicio, Turno
from .forms import CustomUserCreationForm, TurnoForm
from django.contrib.auth.decorators import login_required

def index(request):
    servicios = Servicio.objects.all()
    return render(request, 'index.html', {'servicios': servicios})

def about(request):
    return render(request, 'about.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def servicio_detail(request, servicio_id):
    servicio = get_object_or_404(Servicio, id=servicio_id)
    if request.method == 'POST':
        form = TurnoForm(request.POST)
        if form.is_valid():
            turno = form.save(commit=False)
            turno.servicio = servicio
            turno.usuario = request.user
            turno.save()
            return redirect('index')
    else:
        form = TurnoForm()
    return render(request, 'servicio_detail.html', {
        'servicio': servicio,
        'form': form
    })
