"""Isolated private file storage and randomized safe upload path generators."""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateMediaStorage(FileSystemStorage):
    """
    File storage rooted at settings.PRIVATE_MEDIA_ROOT (outside MEDIA_ROOT).
    Files stored here are NEVER exposed under /media/ and can only be retrieved
    through authenticated, permission-checked views.
    """

    def __init__(self) -> None:
        super().__init__(
            location=settings.PRIVATE_MEDIA_ROOT,
            base_url=None,
            file_permissions_mode=0o640,
            directory_permissions_mode=0o750,
        )

    @property
    def base_location(self) -> str:
        return str(settings.PRIVATE_MEDIA_ROOT)

    @property
    def location(self) -> str:
        return str(Path(settings.PRIVATE_MEDIA_ROOT).resolve())

    def url(self, name: str | None) -> str:
        raise SuspiciousOperation(
            "Direct URL access to private media is forbidden. "
            "Use the authorized protected-media endpoint."
        )


private_media_storage = PrivateMediaStorage()


@deconstructible
class RandomizedUploadTo:
    """
    Generate non-guessable UUIDv4 upload paths while preserving only validated,
    lowercased file extensions. Prevents filename collisions, path traversal,
    and URL enumeration.
    """

    def __init__(self, subdir: str) -> None:
        self.subdir = subdir.strip("/")

    def __call__(self, instance, filename: str) -> str:
        ext = Path(filename or "").suffix.lower()
        if not ext or len(ext) > 10 or not ext[1:].isalnum():
            ext = ".bin"
        today = date.today()
        return f"{self.subdir}/{today:%Y/%m}/{uuid.uuid4().hex}{ext}"


upload_profile_photo = RandomizedUploadTo("profiles")
upload_product_image = RandomizedUploadTo("products")
upload_blog_image = RandomizedUploadTo("blog")
upload_seo_image = RandomizedUploadTo("seo")

upload_private_certificate = RandomizedUploadTo("certificates")
upload_private_medal_evidence = RandomizedUploadTo("medals")
upload_private_activity_photo = RandomizedUploadTo("activities")
