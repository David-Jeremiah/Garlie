from django.conf import settings

from .cart import Cart
from .models import Category


def store(request):
    cart = Cart(request)
    return {
        "STORE_NAME": settings.STORE_NAME,
        "STORE_TAGLINE": settings.STORE_TAGLINE,
        "FREE_SHIPPING_THRESHOLD": settings.FREE_SHIPPING_THRESHOLD,
        "WELCOME_COUPON": settings.WELCOME_COUPON,
        "nav_categories": Category.objects.all(),
        "cart_count": len(cart),
    }
