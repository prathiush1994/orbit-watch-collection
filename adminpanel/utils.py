import base64
import uuid
from django.core.files.base import ContentFile


def save_cropped_image(base64_data, upload_subdir, filename_prefix="img"):
    if not base64_data or not base64_data.startswith("data:image"):
        return None

    try:
        # Strip the "data:image/jpeg;base64," header
        header, encoded = base64_data.split(",", 1)
        image_bytes = base64.b64decode(encoded)

        # Determine extension
        ext = "jpg"
        if "png" in header:
            ext = "png"
        elif "webp" in header:
            ext = "webp"

        filename = f"{filename_prefix}_{uuid.uuid4().hex[:10]}.{ext}"
        return ContentFile(image_bytes, name=filename)

    except Exception:
        return None
