import re
import secrets
import string
from decimal import Decimal
from urllib.parse import quote

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

SITE_SETTINGS_CACHE_KEY = "site_settings"


def _fmt(value):
    """12000.00 -> 12,000 and 12.50 -> 12.5"""
    text = f"{value:,.2f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


class SiteSettings(models.Model):
    """Single-row table holding store-wide settings editable from the admin."""

    store_name = models.CharField(max_length=80, default="Garlie")
    tagline = models.CharField(max_length=160, blank=True)
    free_shipping_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Orders above this get free shipping"
    )
    welcome_coupon = models.CharField(
        max_length=40, blank=True, help_text="Code shown in the banner and footer. Create it under Coupons too."
    )
    whatsapp_number = models.CharField(
        max_length=20,
        blank=True,
        default="256774156366",
        help_text="Orders are sent to this WhatsApp number. Use the country code, e.g. 256774156366 "
        "(0774156366 also works). Leave empty to turn WhatsApp checkout off.",
    )

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce a single row
        super().save(*args, **kwargs)
        cache.delete(SITE_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        cache.delete(SITE_SETTINGS_CACHE_KEY)

    @property
    def whatsapp_link_number(self):
        """Digits only, with country code, ready for https://wa.me/<number>."""
        digits = re.sub(r"\D", "", self.whatsapp_number or "")
        if digits.startswith("00"):
            digits = digits[2:]
        elif digits.startswith("0"):
            digits = "256" + digits[1:]  # Uganda local format
        return digits

    @classmethod
    def load(cls):
        obj = cache.get(SITE_SETTINGS_CACHE_KEY)
        if obj is None:
            # First run: seed the row from the old values in settings.py (if present).
            obj, _ = cls.objects.get_or_create(
                pk=1,
                defaults={
                    "store_name": getattr(settings, "STORE_NAME", "Garlie"),
                    "tagline": getattr(settings, "STORE_TAGLINE", ""),
                    "free_shipping_threshold": Decimal(str(getattr(settings, "FREE_SHIPPING_THRESHOLD", 0))),
                    "welcome_coupon": getattr(settings, "WELCOME_COUPON", ""),
                    "whatsapp_number": getattr(settings, "WHATSAPP_NUMBER", "256774156366"),
                },
            )
            cache.set(SITE_SETTINGS_CACHE_KEY, obj, 300)
        return obj


class Category(models.Model):
    """A scent family: Floral, Oud, Fresh..."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    tagline = models.CharField(max_length=120, blank=True)
    color = models.CharField(max_length=7, default="#b89a6a", help_text="Hex colour used for tints, e.g. #c48b9f")
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"{reverse('shop')}?category={self.slug}"


class Product(models.Model):
    class Gender(models.TextChoices):
        UNISEX = "unisex", "Unisex"
        WOMEN = "women", "For her"
        MEN = "men", "For him"

    class Concentration(models.TextChoices):
        EDT = "Eau de Toilette", "Eau de Toilette"
        EDP = "Eau de Parfum", "Eau de Parfum"
        PARFUM = "Parfum", "Parfum (extrait)"

    class Shape(models.TextChoices):
        CLASSIC = "classic", "Classic"
        TALL = "tall", "Tall"
        ROUND = "round", "Round"

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    tagline = models.CharField(max_length=160, blank=True, help_text="One line shown on cards")
    description = models.TextField(blank=True)
    top_notes = models.CharField(max_length=200, blank=True, help_text="Comma separated")
    heart_notes = models.CharField(max_length=200, blank=True, help_text="Comma separated")
    base_notes = models.CharField(max_length=200, blank=True, help_text="Comma separated")
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.UNISEX)
    concentration = models.CharField(max_length=20, choices=Concentration.choices, default=Concentration.EDP)
    image = models.ImageField(upload_to="products/", blank=True, help_text="Optional. Without it a bottle illustration is drawn.")
    color = models.CharField(max_length=7, default="#b89a6a", help_text="Liquid colour for the bottle illustration")
    bottle_shape = models.CharField(max_length=10, choices=Shape.choices, default=Shape.CLASSIC)
    is_bestseller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product", args=[self.slug])

    @staticmethod
    def _split(value):
        return [part.strip() for part in value.split(",") if part.strip()]

    @property
    def top_list(self):
        return self._split(self.top_notes)

    @property
    def heart_list(self):
        return self._split(self.heart_notes)

    @property
    def base_list(self):
        return self._split(self.base_notes)

    @property
    def default_variant(self):
        """Cheapest variant that is in stock (uses prefetched variants when present)."""
        in_stock = [v for v in self.variants.all() if v.stock > 0]
        return min(in_stock, key=lambda v: v.price) if in_stock else None


class Variant(models.Model):
    """A purchasable size of a product."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    size_ml = models.PositiveSmallIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    compare_at_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Old price, shown struck through"
    )
    stock = models.PositiveIntegerField(default=0)
    sku = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["size_ml"]
        unique_together = [("product", "size_ml")]

    def __str__(self):
        return f"{self.product.name} {self.size_ml}ml"

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def low_stock(self):
        return 0 < self.stock <= 5


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    name = models.CharField(max_length=80)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField()
    is_approved = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.product} - {self.rating}/5 by {self.name}"


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True, help_text="Stored in upper case")
    percent_off = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    min_subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.code} ({self.percent_off}% off)"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def is_valid_for(self, subtotal):
        if not self.active:
            return False, "This code is no longer active."
        if self.expires_at and self.expires_at < timezone.now():
            return False, "This code has expired."
        if subtotal < self.min_subtotal:
            return False, f"This code needs an order of at least {self.min_subtotal}."
        return True, ""


def _order_number():
    alphabet = string.ascii_uppercase + string.digits
    return "GP-" + "".join(secrets.choice(alphabet) for _ in range(8))


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Payment(models.TextChoices):
        COD = "cod", "Pay on delivery"
        MOMO = "momo", "Mobile money (we confirm by phone)"

    number = models.CharField(max_length=14, unique=True, editable=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(max_length=8, choices=Payment.choices, default=Payment.COD)

    full_name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=80)
    country = models.CharField(max_length=80, default="Uganda")
    notes = models.TextField(blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=30, blank=True)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            number = _order_number()
            while Order.objects.filter(number=number).exists():
                number = _order_number()
            self.number = number
        super().save(*args, **kwargs)

    @property
    def whatsapp_url(self):
        """wa.me link with this order pre-filled, or "" if no WhatsApp number is set."""
        number = SiteSettings.load().whatsapp_link_number
        if not number:
            return ""
        sym = getattr(settings, "STORE_CURRENCY_SYMBOL", "")
        lines = [
            f"*New order {self.number}*",
            "",
            f"Name: {self.full_name}",
            f"Phone: {self.phone}",
            f"Email: {self.email}",
            f"Address: {self.address}, {self.city}, {self.country}",
            f"Payment: {self.get_payment_method_display()}",
        ]
        if self.notes:
            lines.append(f"Notes: {self.notes}")
        lines += ["", "*Items*"]
        for item in self.items.all():
            lines.append(f"- {item.quantity} x {item.product_name} {item.size_ml}ml = {sym}{_fmt(item.line_total)}")
        lines.append("")
        if self.discount:
            lines.append(f"Discount: -{sym}{_fmt(self.discount)}")
        if self.shipping:
            lines.append(f"Shipping: {sym}{_fmt(self.shipping)}")
        lines.append(f"*Total: {sym}{_fmt(self.total)}*")
        return f"https://wa.me/{number}?text={quote(chr(10).join(lines), safe='')}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    variant = models.ForeignKey(Variant, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=120)
    size_ml = models.PositiveSmallIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.product_name} {self.size_ml}ml"

    @property
    def line_total(self):
        return self.unit_price * self.quantity


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    handled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.name} ({self.created:%Y-%m-%d})"