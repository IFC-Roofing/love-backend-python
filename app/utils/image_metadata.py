"""
Extract image/video metadata for postcard front/back media.
Images: PIL (width, height, format, size_kb).
Videos: opencv (width, height, duration_seconds, format, size_kb).
"""
from io import BytesIO
from typing import Any, Dict, Optional

try:
    from PIL import Image
except ImportError:
    Image = None  # type: ignore

from app.utils.video_metadata import extract_video_metadata


def extract_image_metadata(content: bytes) -> Dict[str, Any]:
    """
    Extract width, height, format, and size_kb from image bytes.
    Returns dict with media_type="image" (for consistency with extract_media_metadata).
    """
    out = _extract_image_metadata_impl(content)
    out["media_type"] = "image"
    return out


def extract_media_metadata(content: bytes, content_type: Optional[str]) -> Dict[str, Any]:
    """
    Extract metadata for either image or video based on content_type.
    Returns unified dict: media_type ("image"|"video"), width, height, format, size_kb,
    and for video: duration_seconds.
    """
    if content_type and content_type.startswith("video/"):
        return extract_video_metadata(content, content_type)
    # Image (or unknown treated as image attempt)
    out = _extract_image_metadata_impl(content)
    out["media_type"] = "image"
    return out


def _extract_image_metadata_impl(content: bytes) -> Dict[str, Any]:
    """Internal: image metadata without media_type."""
    if Image is None:
        return _size_only_metadata(content)
    try:
        with Image.open(BytesIO(content)) as img:
            width, height = img.size
            fmt = img.format or "unknown"
        size_kb = round(len(content) / 1024.0, 2)
        return {
            "width": width,
            "height": height,
            "format": fmt,
            "size_kb": size_kb,
        }
    except Exception:
        return _size_only_metadata(content)


def _size_only_metadata(content: bytes) -> Dict[str, Any]:
    """Fallback when PIL fails or is missing: at least store size_kb."""
    return {
        "width": None,
        "height": None,
        "format": None,
        "size_kb": round(len(content) / 1024.0, 2),
    }
