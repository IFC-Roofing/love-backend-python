"""
Generate QR code PNG bytes for a URL (e.g. direct S3 video link for postcards).
"""
from io import BytesIO
from typing import Optional

try:
    import qrcode
except ImportError:
    qrcode = None  # type: ignore


def generate_qr_png(url: str, size_px: int = 400, border: int = 2) -> Optional[bytes]:
    """
    Generate a QR code image as PNG bytes for the given URL.

    Args:
        url: The URL to encode (e.g. direct S3 video URL).
        size_px: Approximate size in pixels per side (default 400 for print quality).
        border: Quiet zone / border in modules (default 2).

    Returns:
        PNG bytes, or None if qrcode library is not available.
    """
    if not url or not url.strip():
        return None
    if qrcode is None:
        return None
    box_size = max(1, size_px // 25)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url.strip())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
