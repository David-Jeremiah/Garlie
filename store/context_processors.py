from .cart import Cart
from .models import Category, SiteSettings


def store(request):
    cart = Cart(request)
    site = SiteSettings.load()
    return {
        "STORE_NAME": site.store_name,
        "STORE_TAGLINE": site.tagline,
        "FREE_SHIPPING_THRESHOLD": site.free_shipping_threshold,
        "WELCOME_COUPON": site.welcome_coupon,
        "WHATSAPP_NUMBER": site.whatsapp_link_number,
        "nav_categories": Category.objects.all(),
        "cart_count": len(cart),
    }