# funcionarios/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def format_minutes(total_minutes):
    """
    Converte um total de minutos (pode ser negativo) para o formato HH:MM.
    """
    if total_minutes is None:
        return "00:00"

    is_negative = total_minutes < 0
    total_minutes = abs(total_minutes)
    
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)
    
    sign = "-" if is_negative else ""
    
    return f"{sign}{hours:02d}:{minutes:02d}"