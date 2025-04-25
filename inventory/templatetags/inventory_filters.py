from django.template import Library
from django.template.defaultfilters import floatformat
from django.utils.safestring import mark_safe

register = Library()

@register.filter
def to_kilos(value):
    """Convert pallets to kilos (1 pallet = 9kg)"""
    try:
        kilos = float(value) * 9  # Convert pallets to kilos
        return floatformat(kilos, 2)  # Display with 2 decimal places
    except (ValueError, TypeError):
        return 0

@register.filter
def to_tons(value):
    """Convert pallets to tons (1 pallet = 9kg = 0.009 tons)"""
    try:
        kilos = float(value) * 9  # Convert pallets to kilos
        tons = kilos / 1000  # Convert kilos to tons
        return floatformat(tons, 3)  # Display with 3 decimal places for better precision with tons
    except (ValueError, TypeError):
        return 0

@register.filter
def format_weight(value):
    """Format weight in tons and kilos in two lines with decimal precision"""
    try:
        from decimal import Decimal
        # Convert to total kilos with higher precision
        value_decimal = Decimal(str(value))
        total_kilos = abs(int(value_decimal * 1000))
        # Split into tons and remaining kilos
        tons = total_kilos // 1000
        kilos = total_kilos % 1000
        return mark_safe(f"<div class='weight-display'><div class='tons'>{tons} طن</div><div class='kilos'>{kilos} كيلو</div></div>")
    except (ValueError, TypeError):
        return mark_safe("<div class='weight-display'><div class='tons'>0 طن</div><div class='kilos'>0 كيلو</div></div>")