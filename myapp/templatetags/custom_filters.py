from django import template

# Esto es necesario para que Django reconozca nuestros filtros
register = template.Library()

# Aquí definimos nuestra herramienta (filtro) llamada 'get_item'
@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite acceder a un valor de un diccionario usando una variable como clave.
    Uso en plantilla: {{ mi_diccionario|get_item:mi_variable_de_clave }}
    """
    return dictionary.get(key)