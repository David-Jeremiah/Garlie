from decimal import Decimal

from django import template
from django.conf import settings

register = template.Library()


@register.filter
def money(value):
    if value is None or value == "":
        return ""
    decimals = settings.STORE_CURRENCY_DECIMALS
    return f"{settings.STORE_CURRENCY_SYMBOL}{Decimal(value):,.{decimals}f}"


@register.filter
def stars(value):
    try:
        full = int(round(float(value or 0)))
    except (TypeError, ValueError):
        full = 0
    return "★" * full + "☆" * (5 - full)


@register.filter
def initial(value):
    return (str(value)[:1] or "G").upper()


@register.inclusion_tag("store/_bottle.html")
def bottle(product, animate=False):
    return {"product": product, "animate": animate}
