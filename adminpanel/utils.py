import base64
import uuid
import os
from django.core.files.base import ContentFile


def save_cropped_image(base64_data, upload_subdir, filename_prefix='img'):
    """
    Decodes a base64 DataURL (from the crop modal) and returns a
    Django ContentFile ready to assign to an ImageField.

    Usage in a view:
        from adminpanel.utils import save_cropped_image

        image_data = request.POST.get('logo_image', '')
        if image_data and image_data.startswith('data:image'):
            brand.logo_image = save_cropped_image(image_data, 'photos/brands', 'brand')
            brand.save()

    Returns None if base64_data is empty or invalid.
    """
    if not base64_data or not base64_data.startswith('data:image'):
        return None

    try:
        # Strip the "data:image/jpeg;base64," header
        header, encoded = base64_data.split(',', 1)
        image_bytes = base64.b64decode(encoded)

        # Determine extension
        ext = 'jpg'
        if 'png' in header:
            ext = 'png'
        elif 'webp' in header:
            ext = 'webp'

        filename = f'{filename_prefix}_{uuid.uuid4().hex[:10]}.{ext}'
        return ContentFile(image_bytes, name=filename)

    except Exception:
        return None