from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string

from .models import Order, OrderItem, Variant


class StockError(Exception):
    pass


@transaction.atomic
def create_order(cart, form):
    """Turn the cart into an Order, re-checking and decrementing stock atomically."""
    lines = cart.lines()
    if not lines:
        raise StockError("Your bag is empty.")
    locked = {
        v.pk: v for v in Variant.objects.select_for_update().filter(pk__in=[l.variant.pk for l in lines])
    }
    for line in lines:
        variant = locked[line.variant.pk]
        if variant.stock < line.qty:
            raise StockError(
                f"Sorry, only {variant.stock} left of {line.product.name} {variant.size_ml}ml. Please update your bag."
            )

    totals = cart.totals()
    order = form.save(commit=False)
    order.subtotal = totals["subtotal"]
    order.discount = totals["discount"]
    order.shipping = totals["shipping"]
    order.total = totals["total"]
    order.coupon_code = totals["coupon"].code if totals["coupon"] else ""
    order.save()

    for line in lines:
        variant = locked[line.variant.pk]
        OrderItem.objects.create(
            order=order,
            variant=variant,
            product_name=line.product.name,
            size_ml=variant.size_ml,
            unit_price=variant.price,
            quantity=line.qty,
        )
        variant.stock -= line.qty
        variant.save(update_fields=["stock"])
    return order


def send_order_email(order):
    body = render_to_string("store/email/order_confirmation.txt", {"order": order})
    send_mail(f"Your Garlie order {order.number}", body, None, [order.email], fail_silently=True)
