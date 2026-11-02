from django.db import migrations


def rename(apps, schema_editor):
    S = apps.get_model("store", "SiteSettings")
    for s in S.objects.all():
        if s.store_name in ("Garil", "Garlie", "Garlie Perfumes", "Garlie Perfumes "):
            s.store_name = "Mr. Garil"
        if s.tagline in ("Scent your story", ""):
            s.tagline = "Whisper of Luxury"
        if s.whatsapp_number in ("256774156366", "0774156366", ""):
            s.whatsapp_number = "256768633991"
        s.save()


class Migration(migrations.Migration):
    dependencies = [("store", "0007_favicon_remove_hero_bg")]
    operations = [migrations.RunPython(rename, migrations.RunPython.noop)]
