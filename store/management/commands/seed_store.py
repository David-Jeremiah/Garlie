"""Fill the shop with demo fragrances so you can see it working.

    python manage.py seed_store           # add demo data (safe to re-run)
    python manage.py seed_store --reset   # wipe products first

Replace these with your real products in the admin at /admin/.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand

from store.models import Category, Coupon, Product, Review, Variant

CATEGORIES = [
    ("Floral", "floral", "Soft, romantic and elegant", "#d9a0b4", 1),
    ("Oud", "oud", "Rich, deep and mysterious", "#7a4a2b", 2),
    ("Fresh", "fresh", "Clean, crisp and invigorating", "#6fb3c8", 3),
    ("Oriental", "oriental", "Bold, warm and seductive", "#d39a3b", 4),
    ("Woody", "woody", "Grounded, smoky and calm", "#8a7a55", 5),
]

# name, slug, category slug, tagline, top, heart, base, gender, conc, color, shape, price50, bestseller, new, stock
PRODUCTS = [
    ("Noir Intense", "noir-intense", "oud", "Dark, smooth and impossible to ignore.", "Saffron, Black pepper", "Oud, Rose", "Amber, Leather, Patchouli", "unisex", "Parfum", "#3a1f16", "tall", 89, True, False, 18),
    ("Bloom Essence", "bloom-essence", "floral", "A bouquet that opens like morning light.", "Pear, Bergamot", "Peony, Jasmine, Rose", "White musk, Cedar", "women", "Eau de Parfum", "#e3a7bb", "classic", 79, True, False, 24),
    ("Aqua Fresh", "aqua-fresh", "fresh", "Sea air and citrus on warm skin.", "Lemon, Sea salt, Mint", "Marine accord, Neroli", "Driftwood, Musk", "unisex", "Eau de Toilette", "#7fc0d4", "round", 75, True, False, 30),
    ("Royal Oud", "royal-oud", "oud", "Ceremonial oud wrapped in warm spice.", "Cardamom, Cinnamon", "Oud, Incense", "Sandalwood, Vanilla", "unisex", "Parfum", "#8a5a2b", "classic", 95, True, False, 12),
    ("Velvet Iris", "velvet-iris", "floral", "Powdery iris with a soft, creamy finish.", "Pink pepper, Mandarin", "Iris, Violet", "Vanilla, Tonka bean", "women", "Eau de Parfum", "#b9a1d6", "tall", 85, False, True, 15),
    ("Amber Dusk", "amber-dusk", "oriental", "Golden amber for long evenings.", "Orange blossom, Cardamom", "Amber, Labdanum", "Vanilla, Benzoin, Musk", "unisex", "Eau de Parfum", "#d6902c", "round", 92, False, True, 20),
    ("Cedar and Smoke", "cedar-and-smoke", "woody", "Campfire, cedar and a little leather.", "Juniper, Black tea", "Cedarwood, Birch tar", "Vetiver, Leather", "men", "Eau de Parfum", "#6b5d3e", "tall", 82, False, False, 9),
    ("Citrus Lagoon", "citrus-lagoon", "fresh", "Bright grapefruit and a cool breeze.", "Grapefruit, Yuzu", "Green tea, Basil", "White cedar, Ambrette", "unisex", "Eau de Toilette", "#a9d96c", "classic", 68, False, True, 26),
    ("Rose Nocturne", "rose-nocturne", "floral", "Dark rose with a sweet, jammy edge.", "Raspberry, Lychee", "Damask rose, Geranium", "Patchouli, Amber", "women", "Parfum", "#a8304d", "classic", 98, False, False, 7),
    ("Santal Silk", "santal-silk", "woody", "Creamy sandalwood, soft as a shawl.", "Cardamom, Fig leaf", "Sandalwood, Orris", "Cashmere woods, Musk", "unisex", "Eau de Parfum", "#c9a77c", "round", 90, True, False, 14),
    ("Midnight Saffron", "midnight-saffron", "oriental", "Saffron and honeyed resin after dark.", "Saffron, Bergamot", "Honey, Rose", "Oud, Amber, Vanilla", "unisex", "Parfum", "#9b3a1e", "tall", 110, False, True, 6),
    ("Jasmine Hour", "jasmine-hour", "floral", "Night jasmine over warm, clean skin.", "Mandarin, Green leaves", "Jasmine sambac, Tuberose", "Sandalwood, Musk", "women", "Eau de Toilette", "#f0d9a2", "classic", 72, False, False, 0),
]

REVIEWS = [
    ("noir-intense", "Daniel K.", 5, "My signature", "Lasts all day and I get compliments every time."),
    ("noir-intense", "Sarah M.", 5, "", "Deep and warm without being heavy."),
    ("bloom-essence", "Amina N.", 5, "Perfect for gifting", "Soft floral that does not shout. My sister loved it."),
    ("aqua-fresh", "Peter O.", 4, "", "Great for hot days. I would like it to last a bit longer."),
    ("royal-oud", "Ibrahim S.", 5, "Worth every shilling", "Rich, smooth oud. A little goes a long way."),
]


class Command(BaseCommand):
    help = "Create demo categories, products, reviews and the welcome coupon."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete existing products and categories first.")

    def handle(self, *args, **opts):
        if opts["reset"]:
            Product.objects.all().delete()
            Category.objects.all().delete()

        cats = {}
        for name, slug, tagline, color, pos in CATEGORIES:
            cats[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "tagline": tagline, "color": color, "position": pos}
            )

        for (name, slug, cat, tagline, top, heart, base, gender, conc, color, shape, price, best, new, stock) in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name, "category": cats[cat], "tagline": tagline,
                    "description": f"{tagline} Opens with {top.lower()}, settles into {heart.lower()} and dries down to {base.lower()}.",
                    "top_notes": top, "heart_notes": heart, "base_notes": base,
                    "gender": gender, "concentration": conc, "color": color, "bottle_shape": shape,
                    "is_bestseller": best, "is_new": new, "is_active": True,
                },
            )
            p50 = Decimal(price)
            sizes = [(30, (p50 * Decimal("0.65")).quantize(Decimal("1")), stock), (50, p50, stock), (100, (p50 * Decimal("1.5")).quantize(Decimal("1")), max(stock - 4, 0))]
            for size, p, st in sizes:
                Variant.objects.update_or_create(
                    product=product, size_ml=size,
                    defaults={"price": p, "stock": st, "sku": f"{slug[:6].upper()}-{size}"},
                )

        for slug, who, rating, title, body in REVIEWS:
            Review.objects.get_or_create(product=Product.objects.get(slug=slug), name=who, defaults={"rating": rating, "title": title, "body": body})

        Coupon.objects.get_or_create(code="WELCOME10", defaults={"percent_off": 10})
        self.stdout.write(self.style.SUCCESS(f"Seeded {Category.objects.count()} categories and {Product.objects.count()} products."))
