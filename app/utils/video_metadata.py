"""
Extract video metadata (width, height, duration, format, size_kb) for postcard media.
Uses opencv (cv2) when available; otherwise returns size-only fallback.
"""
import os
import tempfile
from typing import Any, Dict

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore


def extract_video_metadata(content: bytes, content_type: str) -> Dict[str, Any]:
    """
    Extract width, height, duration_seconds, format, size_kb from video bytes.

    Writes to a temp file because cv2.VideoCapture requires a path.
    Returns dict with media_type="video" and optional duration_seconds.
    """
    size_kb = round(len(content) / 1024.0, 2)
    fmt = _format_from_content_type(content_type)
    if cv2 is None:
        return {
            "media_type": "video",
            "width": None,
            "height": None,
            "format": fmt,
            "size_kb": size_kb,
            "duration_seconds": None,
        }
    suffix = _suffix_from_content_type(content_type)
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(content)
            path = f.name
        try:
            cap = cv2.VideoCapture(path)
            try:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or None
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or None
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                duration_seconds = None
                if fps and fps > 0 and frame_count is not None:
                    duration_seconds = round(frame_count / fps, 2)
                return {
                    "media_type": "video",
                    "width": width,
                    "height": height,
                    "format": fmt,
                    "size_kb": size_kb,
                    "duration_seconds": duration_seconds,
                }
            finally:
                cap.release()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass
    except Exception:
        pass
    return {
        "media_type": "video",
        "width": None,
        "height": None,
        "format": fmt,
        "size_kb": size_kb,
        "duration_seconds": None,
    }


def _format_from_content_type(content_type: str) -> str:
    if not content_type:
        return "unknown"
    if "mp4" in content_type:
        return "mp4"
    if "webm" in content_type:
        return "webm"
    if "quicktime" in content_type or "mov" in content_type:
        return "mov"
    return content_type.split("/")[-1].split(";")[0].strip() or "unknown"


def _suffix_from_content_type(content_type: str) -> str:
    if content_type and "webm" in content_type:
        return ".webm"
    if content_type and ("quicktime" in content_type or "mov" in content_type):
        return ".mov"
    return ".mp4"
