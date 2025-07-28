from django.db import migrations
from django.utils.text import slugify # <-- ¡IMPORTANTE! AÑADE ESTA IMPORTACIÓN

def anadir_categorias(apps, schema_editor):
    """
    Crea las categorías iniciales en la base de datos, asegurándose de generar un slug.
    """
    Categoria = apps.get_model('myapp', 'Categoria')
    categorias_a_crear = [
        'Peluquerías',
        'Barberías',
        'Salones de Uñas',
        'Spas y Masajes',
        'Estudios de Tatuajes',
        'Consultorios Médicos',
        'Clases Particulares',
        'Servicios para Mascotas',
        'Gimnasios y Entrenadores',
        'Otra'
    ]
    for nombre_categoria in categorias_a_crear:
        # Generamos el slug a partir del nombre
        slug_generado = slugify(nombre_categoria)
        # Usamos 'defaults' para pasar el slug solo si se va a crear el objeto
        Categoria.objects.get_or_create(
            nombre=nombre_categoria, 
            defaults={'slug': slug_generado}
        )

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'), # Depende de la primera migración que crea el modelo Categoria
    ]

    operations = [
        migrations.RunPython(anadir_categorias),
    ]