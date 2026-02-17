"""
Build front/back HTML for DMM from postcard.
Uses front_image_path and back_image_path as stored in DB (e.g. S3 URLs).
DMM does not support video; for video postcards we send thumbnail + QR (direct S3 link).
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
    if not path:
        return False
    p = path.split("?")[0].lower()
    return any(p.endswith(ext) for ext in VIDEO_EXTENSIONS)


def build_front_html(
    front_image_path: str,
    video_thumbnail_path: Optional[str] = None,
    video_qr_image_path: Optional[str] = None,
) -> str:
    """
    Build front HTML for DMM. For video postcards pass video_thumbnail_path and video_qr_image_path
    so we render thumbnail with QR overlaid (no <video>; DMM does not support video).
    """
    url = (front_image_path or "").strip()
    thumb_url = (video_thumbnail_path or "").strip()
    qr_url = (video_qr_image_path or "").strip()

    if thumb_url and qr_url:
        # Video postcard: thumbnail with QR overlaid (bottom-right)
        content = (
            '<div style="position:relative;width:100%;height:100%;min-height:200px;">'
            f'<img src="{html.escape(thumb_url)}" style="width:100%;height:100%;object-fit:cover;display:block;" alt="Video preview" />'
            '<div style="position:absolute;bottom:12px;right:12px;text-align:center;">'
            f'<img src="{html.escape(qr_url)}" style="width:100px;height:100px;display:block;" alt="QR code" />'
            '<span style="font-size:11px;display:block;margin-top:4px;">Scan to watch</span>'
            "</div>"
            "</div>"
        )
    elif _is_video_url(url):
        # Video but no thumbnail/QR yet: placeholder so DMM never receives <video>
        content = (
            '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#eee;padding:16px;">'
            '<p style="text-align:center;margin:0;">Video – scan QR to watch</p>'
            "</div>"
        )
    else:
        content = f'<div style="width:100%;height:100%;"><img src="{html.escape(url)}" style="width:100%;height:100%;object-fit:cover;" alt="Front" /></div>'
    return _wrap_valid_html(content)


def build_back_html(
    back_image_path: str,
    personal_message: Optional[str] = None,
    qr_code_data: Optional[str] = None,
) -> str:
    url = (back_image_path or "").strip()
    parts = []
    # DMM does not support video; show placeholder if back is video
    if _is_video_url(url):
        parts.append(
            '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:#eee;">'
            '<p style="margin:0;">Video on front – scan QR to watch</p></div>'
        )
    else:
        parts.append(f'<div style="width:100%;height:100%;"><img src="{html.escape(url)}" style="width:100%;height:100%;object-fit:cover;" alt="Back" /></div>')
    if personal_message:
        parts.append(f'<div style="margin-top:8px;white-space:pre-wrap;">{html.escape(personal_message)}</div>')
    if qr_code_data:
        parts.append(f'<div style="margin-top:8px;font-size:10px;">QR: {html.escape(qr_code_data)}</div>')
    return _wrap_valid_html("".join(parts))
