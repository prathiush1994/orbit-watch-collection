import os
import django
import cloudinary

from dotenv import load_dotenv
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orbit.settings")
django.setup()

from cloudinary.uploader import upload
from store.models import ProductVariant, VariantImage
from brands.models import Brand

# ProductVariant images
for item in ProductVariant.objects.all():
    if item.primary_image:
        path = item.primary_image.path
        result = upload(path, folder="photos/variants")
        item.primary_image = result["public_id"]
        item.save()
        print("Uploaded:", path)

# Variant gallery images
for item in VariantImage.objects.all():
    if item.image:
        path = item.image.path
        result = upload(path, folder="photos/variant_gallery")
        item.image = result["public_id"]
        item.save()
        print("Uploaded:", path)

# Brand logos
for item in Brand.objects.all():
    if item.logo_image:
        path = item.logo_image.path
        result = upload(path, folder="photos/brands")
        item.logo_image = result["public_id"]
        item.save()
        print("Uploaded:", path)

print("Done")