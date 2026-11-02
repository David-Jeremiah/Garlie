from decimal import Decimal

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from django.contrib.auth import get_user_model

from .models import Category, Coupon, Order, Product, Profile, Variant

User = get_user_model()


class StoreTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Floral", slug="floral")
        self.product = Product.objects.create(
            name="Bloom", slug="bloom", category=self.cat, top_notes="Pear, Rose", is_bestseller=True
        )
        self.v50 = Variant.objects.create(product=self.product, size_ml=50, price=Decimal("50"), stock=5)
        self.v100 = Variant.objects.create(product=self.product, size_ml=100, price=Decimal("90"), stock=1)
        Coupon.objects.create(code="welcome10", percent_off=10)

    def add(self, variant, qty=1):
        return self.client.post(reverse("cart_add"), {"variant": variant.pk, "qty": qty})

    def checkout_data(self, **extra):
        data = {
            "full_name": "Amaya T", "email": "a@example.com", "phone": "0700000000",
            "address": "Plot 1", "city": "Kampala", "country": "Uganda", "payment_method": "cod",
        }
        data.update(extra)
        return data

    def test_pages_render(self):
        for name, args in [("home", []), ("shop", []), ("product", ["bloom"]), ("cart", []), ("track", []),
                           ("contact", []), ("page", ["about"]), ("page", ["faq"])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200, name)

    def test_unknown_page_404(self):
        self.assertEqual(self.client.get("/nope/").status_code, 404)

    def test_search_and_filter(self):
        self.assertContains(self.client.get(reverse("shop"), {"q": "pear"}), "Bloom")
        self.assertNotContains(self.client.get(reverse("shop"), {"q": "zzz"}), "card-media")

    def test_cart_totals_and_shipping(self):
        self.add(self.v50)  # 50 < 75 -> shipping charged
        t = self.client.get(reverse("cart")).context["t"]
        self.assertEqual(t["subtotal"], Decimal("50"))
        self.assertGreater(t["shipping"], 0)
        self.add(self.v50)  # 100 >= 75 -> free
        t = self.client.get(reverse("cart")).context["t"]
        self.assertEqual(t["shipping"], 0)

    def test_cart_clamps_to_stock(self):
        self.add(self.v100, 5)
        lines = self.client.get(reverse("cart")).context["lines"]
        self.assertEqual(lines[0].qty, 1)

    def test_ajax_add_returns_count(self):
        r = self.client.post(reverse("cart_add"), {"variant": self.v50.pk, "qty": 2}, headers={"x-requested-with": "XMLHttpRequest"})
        self.assertEqual(r.json()["count"], 2)

    def test_coupon(self):
        self.add(self.v50, 2)
        self.client.post(reverse("cart_coupon"), {"code": "WELCOME10"})
        t = self.client.get(reverse("cart")).context["t"]
        self.assertEqual(t["discount"], Decimal("10.00"))
        self.client.post(reverse("cart_coupon"), {"code": "NOPE"})
        self.assertEqual(self.client.get(reverse("cart")).context["t"]["discount"], Decimal("10.00"))

    def test_checkout_creates_order_and_decrements_stock(self):
        self.add(self.v50, 2)
        r = self.client.post(reverse("checkout"), self.checkout_data())
        order = Order.objects.get()
        self.assertRedirects(r, reverse("order_success", args=[order.number]))
        self.v50.refresh_from_db()
        self.assertEqual(self.v50.stock, 3)
        self.assertEqual(order.items.get().quantity, 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(self.client.get(reverse("cart")).context["lines"]), 0)

    def test_checkout_empty_cart_redirects(self):
        self.assertRedirects(self.client.get(reverse("checkout")), reverse("shop"))

    def test_order_page_is_private_but_trackable(self):
        self.add(self.v50, 2)
        self.client.post(reverse("checkout"), self.checkout_data())
        order = Order.objects.get()
        stranger = self.client_class()
        self.assertRedirects(stranger.get(reverse("order_success", args=[order.number])), reverse("track"))
        r = stranger.post(reverse("track"), {"number": order.number.lower(), "email": "A@example.com"})
        self.assertContains(r, order.number)
        r = stranger.post(reverse("track"), {"number": order.number, "email": "wrong@example.com"})
        self.assertNotContains(r, "Amaya")

    def test_newsletter_dedupes(self):
        for _ in range(2):
            self.client.post(reverse("newsletter"), {"email": "x@example.com"})
        from .models import Subscriber
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_review_updates_rating(self):
        self.client.post(reverse("add_review", args=["bloom"]), {"name": "Z", "rating": 4, "body": "Lovely"})
        r = self.client.get(reverse("product", args=["bloom"]))
        self.assertEqual(r.context["product"].rating_count, 1)


class AccountTests(TestCase):
    def signup_data(self, **extra):
        d = {"full_name": "Amaya T", "email": "Amaya@Example.com", "phone": "0700000000",
             "password1": "S3cure-pass-77", "password2": "S3cure-pass-77"}
        d.update(extra)
        return d

    def test_signup_logs_in_and_creates_profile(self):
        r = self.client.post(reverse("signup"), self.signup_data())
        self.assertRedirects(r, reverse("account"))
        page = self.client.get(reverse("account"))
        self.assertContains(page, "Hello, Amaya T")
        user = Profile.objects.get().user
        self.assertEqual(user.username, "amaya@example.com")
        self.assertEqual(user.profile.phone, "0700000000")

    def test_duplicate_email_rejected(self):
        self.client.post(reverse("signup"), self.signup_data())
        self.client.post(reverse("account_logout"))
        r = self.client.post(reverse("signup"), self.signup_data(email="amaya@example.com"))
        self.assertContains(r, "already exists")

    def test_login_logout_and_profile_edit(self):
        self.client.post(reverse("signup"), self.signup_data())
        self.client.post(reverse("account_logout"))
        self.assertRedirects(self.client.get(reverse("account")), reverse("account_login") + "?next=/account/")
        r = self.client.post(reverse("account_login"), {"username": "AMAYA@example.com", "password": "S3cure-pass-77"})
        self.assertRedirects(r, reverse("account"))
        r = self.client.post(reverse("account"), {
            "full_name": "Amaya Tumusiime", "email": "new@example.com", "phone": "0711", "address": "Plot 5",
            "city": "Entebbe", "country": "Uganda"})
        self.assertRedirects(r, reverse("account"))
        user = Profile.objects.get().user
        self.assertEqual((user.first_name, user.email, user.username, user.profile.city),
                         ("Amaya Tumusiime", "new@example.com", "new@example.com", "Entebbe"))
        self.client.post(reverse("account_logout"))
        r = self.client.post(reverse("account_login"), {"username": "new@example.com", "password": "S3cure-pass-77"})
        self.assertRedirects(r, reverse("account"))

    def test_checkout_prefilled_and_order_linked(self):
        cat = Category.objects.create(name="Oud", slug="oud")
        prod = Product.objects.create(name="X", slug="x", category=cat)
        var = Variant.objects.create(product=prod, size_ml=50, price=Decimal("50"), stock=5)
        self.client.post(reverse("signup"), self.signup_data())
        self.client.post(reverse("cart_add"), {"variant": var.pk, "qty": 1})
        self.assertContains(self.client.get(reverse("checkout")), "amaya@example.com")
        self.client.post(reverse("checkout"), {
            "full_name": "Amaya T", "email": "amaya@example.com", "phone": "0700", "address": "Plot 1",
            "city": "Kampala", "country": "Uganda", "payment_method": "cod"})
        order = Order.objects.get()
        self.assertEqual(order.user.email, "amaya@example.com")
        self.assertContains(self.client.get(reverse("account")), order.number)
        self.assertEqual(self.client.get(reverse("account_order", args=[order.number])).status_code, 200)
        self.client.post(reverse("account_logout"))
        other = User.objects.create_user("o@example.com", "o@example.com", "pw-12345-xyz")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("account_order", args=[order.number])).status_code, 404)
