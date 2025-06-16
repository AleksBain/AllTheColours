from django import template

register = template.Library()

@register.filter
def pluck(data, key):
    """
    Filtr do wyciągania wartości klucza z listy słowników
    Przykład: {{ data|pluck:"typ_kolorystyczny__nazwa" }}
    """
    return [item.get(key) for item in data if isinstance(item, dict)]
