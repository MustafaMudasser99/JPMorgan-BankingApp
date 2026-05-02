from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template
from django.utils.text import slugify

register = template.Library()


@register.filter
def format_gbp(value):
    """
    Format a numeric amount for GBP display (always 2 decimal places, no trailing junk).
    """
    if value is None:
        return "0.00"
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return str(value)
    q = d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return format(q, "f")


@register.filter
def account_type_slug(value):
    """
    Converts an account type display name (e.g. "Savers Plus") into a CSS-safe slug
    (e.g. "savers-plus").
    """
    if value is None:
        return ""
    return slugify(str(value))

