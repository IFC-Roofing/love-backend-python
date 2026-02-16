"""
Build front/back HTML for DMM from postcard.
Uses front_image_path and back_image_path as stored in DB (e.g. S3 URLs).
DMM requires valid HTML (full document); we wrap content in minimal HTML5.
"""
import html
from typing import Optional

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov")


def _wrap_valid_html(body_content: str) -> str:
    """Wrap fragment in minimal valid HTML5 document so DMM accepts it."""
    return (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset=\"UTF-8\"></head><body>"
        f"{body_content}"
        "</body></html>"
    )


def _is_video_url(path: str) -> bool:
    p = path.split("?")[0].lower()
    return any(p.endswith(ext) for ext in VIDEO_EXTENSIONS)


def build_front_html(front_image_path: str) -> str:
    url = front_image_path.strip()
    if _is_video_url(url):
        content = f'<div style="width:100%;height:100%;"><video src="{html.escape(url)}" style="width:100%;height:100%;object-fit:cover;" muted playsinline></video></div>'
    else:
        content = f'<div style="width:100%;height:100%;"><img src="{html.escape(url)}" style="width:100%;height:100%;object-fit:cover;" alt="Front" /></div>'
    return _wrap_valid_html(content)


def build_back_html(
    back_image_path: str,
    personal_message: Optional[str] = None,
    qr_code_data: Optional[str] = None,
) -> str:
    url = back_image_path.strip()
    parts = []
    if _is_video_url(url):
        parts.append(f'<div style="width:100%;height:100%;"><video src="{html.escape(url)}" style="width:100%;height:100%;object-fit:cover;" muted playsinline></video></div>')
    else:
        parts.append(f'<div style="width:100%;height:100%;"><img src="{html.escape(url)}" style="width:100%;height:100%;object-fit:cover;" alt="Back" /></div>')
    if personal_message:
        parts.append(f'<div style="margin-top:8px;white-space:pre-wrap;">{html.escape(personal_message)}</div>')
    if qr_code_data:
        parts.append(f'<div style="margin-top:8px;font-size:10px;">QR: {html.escape(qr_code_data)}</div>')
    return _wrap_valid_html("".join(parts))
