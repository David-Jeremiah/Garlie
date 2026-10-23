# Garlie Perfumes (Django)

A full ecommerce storefront: catalogue with filters and search, product pages with sizes
and scent notes, session cart, discount codes, guest checkout, order tracking, reviews,
newsletter, and an admin to manage everything.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_store        # demo perfumes + WELCOME10 coupon
python manage.py createsuperuser   # for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and the admin at http://127.0.0.1:8000/admin/.
Run the tests with `python manage.py test`.

## Make it yours

| What | Where |
|---|---|
| Name, currency, free-shipping amount, flat shipping | bottom of `config/settings.py` |
| Products, sizes, stock, prices, photos | Admin > Products (sizes are inline) |
| Orders: mark paid, shipped, delivered | Admin > Orders (bulk actions) |
| Discount codes | Admin > Coupons |
| About, shipping, returns, FAQ text | `PAGES` in `store/views.py` |
| Colours and fonts | `:root` at the top of `static/css/garlie.css` |

Currency for Uganda: set `STORE_CURRENCY_SYMBOL = "UGX "` and `STORE_CURRENCY_DECIMALS = 0`,
then update the prices, `FREE_SHIPPING_THRESHOLD` and `FLAT_SHIPPING` to shillings.

Product photos: upload an image on a product and it replaces the drawn bottle everywhere.
Leaving the image empty keeps the bottle illustration, tinted with the product's colour.

## How checkout works

Guests check out without an account. Payment is "pay on delivery" or "mobile money (we confirm
by phone)": no money moves online. Orders start as Pending, stock is reduced at order time
(re-checked inside a transaction so two buyers cannot take the last bottle), and a confirmation
email is sent (printed to the terminal until you configure SMTP).

To take card or mobile-money payments online, add a gateway (Stripe, Flutterwave, Pesapal, etc.)
in `store/views.py::checkout` after `create_order(...)` and redirect to its hosted payment page.

## Going live checklist

- Set environment variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`,
  `DJANGO_CSRF_TRUSTED_ORIGINS` (e.g. `https://garlie.example`).
- Configure email (`DJANGO_EMAIL_BACKEND` + SMTP settings) and `DJANGO_FROM_EMAIL`.
- Use PostgreSQL instead of SQLite; run `python manage.py collectstatic`; serve static files with
  WhiteNoise or your web server, and serve `media/` (uploaded photos) from your web server or storage.
- Run behind gunicorn with HTTPS.

## Structure

```
config/        settings, urls, wsgi
store/         models, views, cart (session), services (order creation), admin, tests
store/management/commands/seed_store.py   demo data
templates/     base + store pages
static/        css/garlie.css, js/garlie.js
```
