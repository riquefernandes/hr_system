from django import template

register = template.Library()

@register.filter
def format_minutes(minutes):
    """Converts minutes into HH:MM format."""
    if minutes is None:
        return "00:00"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours:02d}:{mins:02d}"
