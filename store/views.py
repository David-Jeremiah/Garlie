from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Min, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm, ContactForm, NewsletterForm, ProfileForm, ReviewForm, SignupForm, TrackForm
from .models import Category, Order, Page, Product, Profile, SiteSettings, Subscriber, Variant
from .services import StockError, create_order, send_contact_email, send_order_email


def products_qs():
    return (
        Product.objects.filter(is_active=True)
        .select_related("category")
        .prefetch_related("variants")
        .annotate(
            price_from=Min("variants__price"),
            rating_avg=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
            rating_count=Count("reviews", filter=Q(reviews__is_approved=True), distinct=True),
        )
    )


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


# --- Browsing -----------------------------------------------------------------
def home(request):
    qs = products_qs()
    bestsellers = list(qs.filter(is_bestseller=True)[:4])
    context = {
        "featured": bestsellers[0] if bestsellers else qs.first(),
        "categories": Category.objects.annotate(n=Count("products", filter=Q(products__is_active=True))),
        "bestsellers": bestsellers,
        "all_products": qs.order_by("-is_bestseller", "-created"),
        "new_arrivals": qs.filter(is_new=True)[:4],
    }
    return render(request, "store/home.html", context)


SORTS = {
    "featured": ("-is_bestseller", "-created"),
    "newest": ("-created",),
    "price-asc": ("price_from",),
    "price-desc": ("-price_from",),
    "rating": ("-rating_avg", "-rating_count"),
}


def shop(request):
    qs = products_qs()
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    gender = request.GET.get("gender", "")
    sort = request.GET.get("sort", "featured")
    max_price = request.GET.get("max_price", "")

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(tagline__icontains=q)
            | Q(top_notes__icontains=q)
            | Q(heart_notes__icontains=q)
            | Q(base_notes__icontains=q)
            | Q(category__name__icontains=q)
        )
    if category:
        qs = qs.filter(category__slug=category)
    if gender in dict(Product.Gender.choices):
        qs = qs.filter(gender=gender)
    if max_price.isdigit():
        qs = qs.filter(price_from__lte=int(max_price))
    qs = qs.order_by(*SORTS.get(sort, SORTS["featured"]))

    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "page": page,
        "q": q,
        "active_category": Category.objects.filter(slug=category).first(),
        "categories": Category.objects.all(),
        "genders": Product.Gender.choices,
        "sorts": [
            ("featured", "Featured"),
            ("newest", "Newest"),
            ("price-asc", "Price: low to high"),
            ("price-desc", "Price: high to low"),
            ("rating", "Top rated"),
        ],
        "sel": {"category": category, "gender": gender, "sort": sort, "max_price": max_price},
        "querystring": params.urlencode(),
    }
    return render(request, "store/shop.html", context)


def product_detail(request, slug):
    product = get_object_or_404(products_qs(), slug=slug)
    variants = list(product.variants.all())
    context = {
        "product": product,
        "variants": variants,
        "first_available": _preferred_variant(variants),
        "reviews": product.reviews.filter(is_approved=True)[:20],
        "review_form": ReviewForm(),
        "related": products_qs().filter(category=product.category).exclude(pk=product.pk)[:4],
    }
    return render(request, "store/product.html", context)


def _preferred_variant(variants):
    """Pre-select 50ml when available, otherwise the first size in stock."""
    available = [v for v in variants if v.in_stock]
    return next((v for v in available if v.size_ml == 50), available[0] if available else None)


@require_POST
def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    form = ReviewForm(request.POST)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.save()
        messages.success(request, "Thank you, your review is live.")
    else:
        messages.error(request, "Please add your name, a rating and a few words.")
    return redirect(f"{product.get_absolute_url()}#reviews")


# --- Cart ---------------------------------------------------------------------
def cart_detail(request):
    cart = Cart(request)
    return render(request, "store/cart.html", {"cart": cart, "lines": cart.lines(), "t": cart.totals()})


@require_POST
def cart_add(request):
    cart = Cart(request)
    variant = get_object_or_404(
        Variant.objects.select_related("product"),
        pk=request.POST.get("variant"),
        product__is_active=True,
    )
    try:
        qty = max(1, int(request.POST.get("qty", 1)))
    except ValueError:
        qty = 1
    if not variant.in_stock:
        message, ok = f"{variant.product.name} {variant.size_ml}ml is sold out.", False
    else:
        cart.add(variant, qty)
        message, ok = f"{variant.product.name} {variant.size_ml}ml added to your bag.", True
    if _is_ajax(request):
        return JsonResponse({"ok": ok, "message": message, "count": len(cart)}, status=200 if ok else 409)
    (messages.success if ok else messages.error)(request, message)
    return redirect("cart" if ok else request.META.get("HTTP_REFERER", "shop"))


@require_POST
def cart_update(request):
    cart = Cart(request)
    variant = get_object_or_404(Variant, pk=request.POST.get("variant"))
    try:
        cart.set(variant, int(request.POST.get("qty", 1)))
    except ValueError:
        pass
    return redirect("cart")


@require_POST
def cart_remove(request):
    Cart(request).remove(request.POST.get("variant", ""))
    return redirect("cart")


@require_POST
def cart_coupon(request):
    cart = Cart(request)
    if request.POST.get("action") == "remove":
        cart.remove_coupon()
        messages.info(request, "Discount code removed.")
    else:
        ok, message = cart.apply_coupon(request.POST.get("code", ""))
        (messages.success if ok else messages.error)(request, message)
    return redirect(request.POST.get("next") or "cart")


# --- Checkout & orders --------------------------------------------------------
def checkout(request):
    cart = Cart(request)
    if not cart.lines():
        messages.info(request, "Your bag is empty. Add a fragrance to check out.")
        return redirect("shop")

    initial = {}
    if request.user.is_authenticated:
        prof, _ = Profile.objects.get_or_create(user=request.user)
        initial = {
            "full_name": request.user.first_name, "email": request.user.email, "phone": prof.phone,
            "address": prof.address, "city": prof.city, "country": prof.country,
        }
    form = CheckoutForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        if request.user.is_authenticated:
            form.instance.user = request.user
        try:
            order = create_order(cart, form)
        except StockError as exc:
            messages.error(request, str(exc))
            return redirect("cart")
        cart.clear()
        recent = request.session.get("recent_orders", [])
        request.session["recent_orders"] = recent + [order.number]
        send_order_email(order)
        wa_url = order.whatsapp_url
        if wa_url:
            return redirect(wa_url)  # opens WhatsApp with the order pre-filled
        return redirect("order_success", number=order.number)
    return render(request, "store/checkout.html", {"form": form, "lines": cart.lines(), "t": cart.totals()})


def order_success(request, number):
    if number not in request.session.get("recent_orders", []):
        messages.info(request, "Enter your order number and email to view an order.")
        return redirect("track")
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    return render(request, "store/order_success.html", {"order": order})


def track_order(request):
    form = TrackForm(request.POST or None)
    order = None
    if request.method == "POST" and form.is_valid():
        order = (
            Order.objects.prefetch_related("items")
            .filter(number=form.cleaned_data["number"].strip().upper(), email__iexact=form.cleaned_data["email"])
            .first()
        )
        if not order:
            messages.error(request, "We could not find an order with those details.")
    return render(request, "store/track.html", {"form": form, "order": order})


# --- Marketing & pages ----------------------------------------------------------
@require_POST
def newsletter(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        _, created = Subscriber.objects.get_or_create(email=form.cleaned_data["email"].lower())
        coupon = SiteSettings.load().welcome_coupon
        if not created:
            message = "You are already on the list."
        elif coupon:
            message = f"You are subscribed. Use {coupon} for 10% off your first order."
        else:
            message = "You are subscribed. Thank you."
        ok = True
    else:
        message, ok = "Please enter a valid email address.", False
    if _is_ajax(request):
        return JsonResponse({"ok": ok, "message": message})
    (messages.success if ok else messages.error)(request, message)
    return redirect(request.META.get("HTTP_REFERER", "home"))


PAGES = {
    "about": {
        "title": "About Garlie",
        "intro": "Perfume that tells your story, one note at a time.",
        "sections": [
            ("Our approach", "Every Garlie fragrance is built around a clear idea: a few well-chosen notes that open bright, settle warm and stay with you. Edit this text to tell your own story."),
            ("Quality", "Each scent lists its top, heart and base notes so you know what you are wearing before you buy."),
        ],
    },
    "shipping": {
        "title": "Shipping and delivery",
        "intro": "Orders over the free-shipping amount ship free.",
        "sections": [
            ("Rates", ""),  # filled in from Site settings in page()
            ("Delivery times", "Add your delivery times and areas here."),
            ("Tracking", "Use Track your order with your order number and email to see the latest status."),
        ],
    },
    "returns": {
        "title": "Returns and exchanges",
        "intro": "Not right for you? Tell us.",
        "sections": [
            ("Policy", "Add your return window and conditions here, for example unopened bottles within 30 days."),
            ("How to start", "Contact us with your order number and we will take it from there."),
        ],
    },
    "faq": {
        "title": "Frequently asked questions",
        "intro": "Quick answers.",
        "sections": [
            ("How long does a fragrance last?", "It depends on the concentration. Parfum lasts longest, then Eau de Parfum, then Eau de Toilette."),
            ("How do I pay?", "Choose pay on delivery or mobile money at checkout. We confirm mobile money orders by phone."),
            ("Can I change my order?", "Contact us as soon as possible with your order number."),
        ],
    },
}


def page(request, slug):
    obj = Page.objects.filter(slug=slug).first()
    if obj:
        sections = obj.sections()
        if slug == "shipping":
            site = SiteSettings.load()
            sym = settings.STORE_CURRENCY_SYMBOL
            rates = (
                f"Free shipping on orders over {sym}{site.free_shipping_threshold:,.0f}. "
                f"Otherwise a flat {sym}{settings.FLAT_SHIPPING}."
            )
            sections = [(h, [p.replace("{rates}", rates) for p in ps]) for h, ps in sections]
        data = {"title": obj.title, "intro": obj.intro, "sections": sections, "image_url": obj.image_url}
        return render(request, "store/page.html", {"page": data})
    data = PAGES.get(slug)
    if not data:
        raise Http404
    data = {**data, "sections": [(h, [t]) for h, t in data["sections"]], "image_url": ""}
    return render(request, "store/page.html", {"page": data})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        send_contact_email(form.save())
        messages.success(request, "Thanks, we have your message and will reply by email.")
        return redirect("contact")
    return render(request, "store/contact.html", {"form": form})

# --- Customer accounts -------------------------------------------------------
def signup(request):
    if request.user.is_authenticated:
        return redirect("account")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your account is ready.")
        return redirect(request.POST.get("next") or "account")
    return render(request, "store/account/signup.html", {"form": form, "next": request.GET.get("next", "")})


@login_required
def account(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile was updated.")
        return redirect("account")
    orders = request.user.orders.prefetch_related("items")[:20]
    return render(request, "store/account/account.html", {"form": form, "orders": orders, "profile": profile})


@login_required
def account_order(request, number):
    order = get_object_or_404(request.user.orders.prefetch_related("items"), number=number)
    return render(request, "store/account/order.html", {"order": order})


@login_required
def password_change(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password was changed.")
        return redirect("account")
    return render(request, "store/account/password.html", {"form": form})
