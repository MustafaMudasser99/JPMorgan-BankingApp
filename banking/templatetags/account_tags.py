from django import template
from django.utils.text import slugify

register = template.Library()


@register.filter
def account_type_slug(value):
    """
    Converts an account type display name (e.g. "Savers Plus") into a CSS-safe slug
    (e.g. "savers-plus").
    """
    if value is None:
        return ""
    return slugify(str(value))

