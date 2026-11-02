from django.db import migrations

PAGES = [
    ("about", "About Mr. Garil", "Whisper of Luxury.",
     "## Our story\nMr. Garil Parfums is a Kampala perfume house, established in 2026. We bring authentic international fragrances to Uganda. Edit this text in Admin > Pages to tell your own story.\n\n"
     "## Delivery\nWe deliver around Kampala and beyond. Order on the website or on WhatsApp and we bring it to you."),
    ("shipping", "Shipping and delivery", "Fast delivery around Kampala and beyond.",
     "## Rates\n{rates}\n\n## Delivery times\nAdd your delivery times and areas here.\n\n## Tracking\nUse Track your order with your order number and email to see the latest status."),
    ("returns", "Returns and exchanges", "Not right for you? Tell us.",
     "## Policy\nAdd your return window and conditions here, for example unopened bottles within 30 days.\n\n## How to start\nContact us with your order number and we will take it from there."),
    ("faq", "Frequently asked questions", "Quick answers.",
     "## How long does a fragrance last?\nIt depends on the concentration. Parfum lasts longest, then Eau de Parfum, then Eau de Toilette.\n\n"
     "## How do I pay?\nChoose pay on delivery or mobile money at checkout. We confirm mobile money orders by phone.\n\n"
     "## Can I change my order?\nContact us as soon as possible with your order number."),
]


def seed(apps, schema_editor):
    Page = apps.get_model("store", "Page")
    for slug, title, intro, body in PAGES:
        Page.objects.get_or_create(slug=slug, defaults={"title": title, "intro": intro, "body": body})


class Migration(migrations.Migration):
    dependencies = [("store", "0005_pages_and_hero_background")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
