from django.db import migrations


def set_offer_flags(apps, schema_editor):
    Category = apps.get_model('category', 'Category')
    NO_OFFER_SLUGS = {'men', 'women', 'kids'}
    Category.objects.filter(slug__in=NO_OFFER_SLUGS).update(is_offer_applicable=False)


class Migration(migrations.Migration):

    dependencies = [
        ('category', '0004_alter_category_is_offer_applicable'), 
    ]

    operations = [
        migrations.RunPython(set_offer_flags, migrations.RunPython.noop),
    ]