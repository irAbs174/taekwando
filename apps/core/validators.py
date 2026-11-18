"""Server-side file upload and input validators."""
from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_PIXELS = 25_000_000  # 25 MP ceiling to prevent decompression bombs
MAX_IMAGE_DIMENSION = 8000

_IMAGE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}

_DANGEROUS_PDF_TOKENS = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile", b"/OpenAction")
_PHONE_RE = re.compile(r"^\+?[0-9\-\s()]{7,22}$")


def _check_file_size(uploaded_file) -> None:
    max_bytes = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024)
    max_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 5)
    if uploaded_file.size > max_bytes:
        raise ValidationError(
            _("File size cannot exceed %(max_mb)s MB."),
            code="file_too_large",
            params={"max_mb": max_mb},
        )
    if uploaded_file.size == 0:
        raise ValidationError(_("Uploaded file is empty."), code="file_empty")


def _verify_image_content(uploaded_file, ext: str) -> None:
    pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(16)
        allowed_sigs = _IMAGE_SIGNATURES.get(ext, ())
        if not any(header.startswith(sig) for sig in allowed_sigs):
            raise ValidationError(
                _("File header does not match a valid image format."),
                code="invalid_image_signature",
            )
        if ext == ".webp" and header[8:12] != b"WEBP":
            raise ValidationError(
                _("Invalid WebP image file."),
                code="invalid_webp",
            )

        uploaded_file.seek(0)
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        try:
            with Image.open(uploaded_file) as img:
                width, height = img.size
                if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
                    raise ValidationError(
                        _("Image dimensions exceed the maximum allowed size."),
                        code="image_dimensions_too_large",
                    )
                fmt = (img.format or "").upper()
                if fmt not in {"JPEG", "PNG", "WEBP"}:
                    raise ValidationError(
                        _("Unsupported image format. Use JPEG, PNG, or WebP."),
                        code="unsupported_image_format",
                    )
                img.verify()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as exc:
            raise ValidationError(
                _("The uploaded file is not a valid or safe image."),
                code="corrupt_image",
            ) from exc
    finally:
        uploaded_file.seek(pos)


def _verify_pdf_content(uploaded_file) -> None:
    pos = uploaded_file.tell() if hasattr(uploaded_file, "tell") else 0
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(8)
        if not header.startswith(b"%PDF-"):
            raise ValidationError(
                _("The uploaded file is not a valid PDF document."),
                code="invalid_pdf",
            )
        uploaded_file.seek(0)
        content = uploaded_file.read(getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024))
        for token in _DANGEROUS_PDF_TOKENS:
            if token in content:
                raise ValidationError(
                    _("PDF files containing embedded scripts or actions are not permitted."),
                    code="unsafe_pdf",
                )
    finally:
        uploaded_file.seek(pos)


@deconstructible
class SafeImageValidator:
    """Validate uploaded images by size, extension, magic bytes, and Pillow decode."""

    def __call__(self, uploaded_file) -> None:
        if not uploaded_file:
            return
        # Skip re-validation of unchanged persisted FieldFile without open upload buffer
        if hasattr(uploaded_file, "_committed") and uploaded_file._committed:
            return
        _check_file_size(uploaded_file)
        name = Path(uploaded_file.name or "").name
        ext = Path(name).suffix.lower()
        allowed = getattr(settings, "ALLOWED_IMAGE_EXTENSIONS", {".jpg", ".jpeg", ".png", ".webp"})
        if ext not in allowed:
            raise ValidationError(
                _("Allowed image formats: JPG, JPEG, PNG, WebP."),
                code="invalid_image_extension",
            )
        _verify_image_content(uploaded_file, ext)


@deconstructible
class SafeDocumentValidator:
    """Validate uploaded certificates and evidence (PDF, JPG, JPEG, PNG, WebP)."""

    def __call__(self, uploaded_file) -> None:
        if not uploaded_file:
            return
        if hasattr(uploaded_file, "_committed") and uploaded_file._committed:
            return
        _check_file_size(uploaded_file)
        name = Path(uploaded_file.name or "").name
        ext = Path(name).suffix.lower()
        allowed = getattr(
            settings,
            "ALLOWED_DOCUMENT_EXTENSIONS",
            {".pdf", ".jpg", ".jpeg", ".png", ".webp"},
        )
        if ext not in allowed:
            raise ValidationError(
                _("Allowed document formats: PDF, JPG, JPEG, PNG, WebP."),
                code="invalid_document_extension",
            )
        if ext == ".pdf":
            _verify_pdf_content(uploaded_file)
        else:
            _verify_image_content(uploaded_file, ext)


validate_safe_image = SafeImageValidator()
validate_safe_document = SafeDocumentValidator()


def validate_phone_number(value: str) -> None:
    if not value:
        return
    if not _PHONE_RE.match(value.strip()):
        raise ValidationError(
            _("Enter a valid phone number (digits, spaces, +, -, parentheses)."),
            code="invalid_phone",
        )
