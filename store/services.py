from django.core.mail import EmailMessage
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


def _site():
    from .models import SiteSettings
    return SiteSettings.load()


def send_order_email(order):
    """Confirmation to the customer, and a full copy of the order to the business email."""
    site = _site()
    body = render_to_string("store/email/order_confirmation.txt", {"order": order, "store_name": site.store_name, "site": site})
    reply_to = [site.email] if site.email else None
    send_mail_safe(f"Your {site.store_name} order {order.number}", body, [order.email], reply_to)
    if site.email:
        lines = [
            f"New order {order.number}",
            f"Customer: {order.full_name}",
            f"Phone: {order.phone}",
            f"Email: {order.email}",
            f"Address: {order.address}, {order.city}, {order.country}",
            f"Payment: {order.get_payment_method_display()}",
        ]
        if order.notes:
            lines.append(f"Notes: {order.notes}")
        lines.append("")
        lines += [f"- {i.quantity} x {i.product_name} {i.size_ml}ml = {i.line_total:,.0f}" for i in order.items.all()]
        lines += ["", f"Shipping: {order.shipping:,.0f}", f"Total: {order.total:,.0f}"]
        send_mail_safe(f"New order {order.number} from {order.full_name}", "\n".join(lines), [site.email], [order.email])


def send_contact_email(message):
    """A website contact-form message goes to the business email; replying goes to the customer."""
    site = _site()
    if not site.email:
        return
    body = f"From: {message.name} <{message.email}>\n\n{message.message}"
    send_mail_safe(f"New message from {message.name}", body, [site.email], [message.email])


def send_mail_safe(subject, body, to, reply_to=None):
    EmailMessage(subject, body, None, to, reply_to=reply_to).send(fail_silently=True)
