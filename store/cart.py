"""Session-based shopping cart. Guests can check out without an account."""
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from .models import Coupon, Variant

CART_KEY = "cart"
COUPON_KEY = "coupon"


@dataclass
class Line:
    variant: Variant
    qty: int

    @property
    def product(self):
        return self.variant.product

    @property
    def unit_price(self):
        return self.variant.price

    @property
    def total(self):
        return self.variant.price * self.qty


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.data = self.session.setdefault(CART_KEY, {})
        self._lines = None

    def _touch(self):
        self.session.modified = True
        self._lines = None

    def _clamp(self, variant, qty):
        return max(0, min(qty, variant.stock, settings.MAX_QTY_PER_LINE))

    def add(self, variant, qty=1):
        current = self.data.get(str(variant.pk), 0)
        self.set(variant, current + qty)

    def set(self, variant, qty):
        qty = self._clamp(variant, qty)
        if qty:
            self.data[str(variant.pk)] = qty
        else:
            self.data.pop(str(variant.pk), None)
        self._touch()

    def remove(self, variant_id):
        self.data.pop(str(variant_id), None)
        self._touch()

    def clear(self):
        self.session.pop(CART_KEY, None)
        self.session.pop(COUPON_KEY, None)
        self.data = {}
        self._touch()

    def lines(self):
        if self._lines is None:
            variants = Variant.objects.select_related("product", "product__category").in_bulk(
                [int(k) for k in self.data]
            )
            lines = []
            for key, qty in list(self.data.items()):
                variant = variants.get(int(key))
                if variant is None or not variant.product.is_active or variant.stock == 0:
                    self.data.pop(key)  # product vanished or sold out
                    self.session.modified = True
                    continue
                qty = min(qty, variant.stock)
                lines.append(Line(variant, qty))
            self._lines = lines
        return self._lines

    def __len__(self):
        return sum(line.qty for line in self.lines())

    # -- coupon -----------------------------------------------------------------
    def coupon(self):
        code = self.session.get(COUPON_KEY)
        if not code:
            return None
        coupon = Coupon.objects.filter(code=code).first()
        if coupon and coupon.is_valid_for(self.subtotal())[0]:
            return coupon
        return None

    def apply_coupon(self, code):
        coupon = Coupon.objects.filter(code=code.strip().upper()).first()
        if not coupon:
            return False, "We could not find that code."
        ok, reason = coupon.is_valid_for(self.subtotal())
        if not ok:
            return False, reason
        self.session[COUPON_KEY] = coupon.code
        self.session.modified = True
        return True, f"{coupon.code} applied: {coupon.percent_off}% off."

    def remove_coupon(self):
        self.session.pop(COUPON_KEY, None)
        self.session.modified = True

    # -- totals -----------------------------------------------------------------
    def subtotal(self):
        return sum((line.total for line in self.lines()), Decimal("0"))

    def totals(self):
        subtotal = self.subtotal()
        coupon = self.coupon()
        discount = (subtotal * coupon.percent_off / Decimal(100)).quantize(Decimal("0.01")) if coupon else Decimal("0")
        threshold = Decimal(str(settings.FREE_SHIPPING_THRESHOLD))
        if not self.lines() or subtotal >= threshold:
            shipping = Decimal("0")
        else:
            shipping = Decimal(str(settings.FLAT_SHIPPING))
        return {
            "subtotal": subtotal,
            "discount": discount,
            "shipping": shipping,
            "total": subtotal - discount + shipping,
            "coupon": coupon,
            "free_shipping_threshold": threshold,
            "free_shipping_remaining": max(threshold - subtotal, Decimal("0")),
            "free_shipping_progress": int(min(subtotal / threshold, 1) * 100) if threshold else 100,
        }
