"""
Postcards API: create, list (page/limit), get by id.
"""
import json
import logging
import os
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import validate_session
from app.core.exceptions import NotFound
from app.crud import contact_crud, postcard_crud
from app.schema.postcard import (
    PostcardCreateResponse,
    PostcardDataIn,
    PostcardListItem,
    PostcardListResponse,
    PostcardResponse,
)
from app.utils.image_metadata import extract_media_metadata
from app.utils.video_metadata import extract_video_thumbnail_frame
from app.aws.s3 import upload_to_s3

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
ALLOWED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm", "video/quicktime"}
ALLOWED_CONTENT_TYPES = ALLOWED_IMAGE_CONTENT_TYPES | ALLOWED_VIDEO_CONTENT_TYPES
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm", ".mov"}


def _safe_extension(filename: str, content_type: Optional[str]) -> str:
    """Return a safe extension for the media (image or video)."""
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ALLOWED_EXTENSIONS:
            return ext
    if content_type in ("image/png", "image/x-png"):
        return ".png"
    if content_type == "image/webp":
        return ".webp"
    if content_type in ("video/mp4", "video/x-mp4"):
        return ".mp4"
    if content_type == "video/webm":
        return ".webm"
    if content_type in ("video/quicktime", "video/x-quicktime"):
        return ".mov"
    if content_type and content_type.startswith("image/"):
        return ".jpg"
    if content_type and content_type.startswith("video/"):
        return ".mp4"
    return ".jpg"


def _ensure_upload_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


@router.post("", response_model=PostcardCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_postcard(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    front_file: UploadFile = File(...),
    back_file: UploadFile = File(...),
    data: Optional[str] = Form(None, description="Optional JSON: personal_message, qr_code_data, design_metadata, receiver_contact_id. All fields optional; omit or send {}."),
):
    """
    Create a postcard: upload front and back media (images or videos). Optional JSON data.
    Returns 'Postcard sent successfully' with the created postcard. Requires Bearer token.
    """
    user_id = uuid.UUID(current_user["user_id"])

    raw = (data or "").strip() or "{}"
    try:
        payload = PostcardDataIn.model_validate(json.loads(raw))
    except (json.JSONDecodeError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_DATA", "message": "Invalid JSON in 'data' field.", "hint": str(e)},
        )

    receiver_contact_id = getattr(payload, "receiver_contact_id", None)
    if receiver_contact_id is not None:
        contact = contact_crud.get_by_user_and_id(db, user_id=user_id, contact_id=receiver_contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_CONTACT", "message": "Receiver contact not found or does not belong to you."},
            )

    if front_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE",
                "message": "Front file must be an image (JPEG, PNG, WebP) or video (MP4, WebM, MOV).",
            },
        )
    if back_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FILE",
                "message": "Back file must be an image (JPEG, PNG, WebP) or video (MP4, WebM, MOV).",
            },
        )

    postcard_id = uuid.uuid4()
    front_ext = _safe_extension(front_file.filename or "", front_file.content_type)
    back_ext = _safe_extension(back_file.filename or "", back_file.content_type)

    front_content = await front_file.read()
    back_content = await back_file.read()

    front_meta = extract_media_metadata(front_content, front_file.content_type)
    back_meta = extract_media_metadata(back_content, back_file.content_type)
    image_metadata = {"front": front_meta, "back": back_meta}

    if settings.use_s3:
        # Store in S3; save full URL in DB for accessible links
        front_key = f"postcards/{postcard_id}/front{front_ext}"
        back_key = f"postcards/{postcard_id}/back{back_ext}"
        front_image_path = upload_to_s3(
            key=front_key,
            body=front_content,
            content_type=front_file.content_type or "application/octet-stream",
        )
        back_image_path = upload_to_s3(
            key=back_key,
            body=back_content,
            content_type=back_file.content_type or "application/octet-stream",
        )
    else:
        # Local storage: write to disk, store relative path
        base_dir = os.path.join(settings.UPLOAD_DIR, "postcards", str(postcard_id))
        _ensure_upload_dir(base_dir)
        front_path = os.path.join(base_dir, f"front{front_ext}")
        back_path = os.path.join(base_dir, f"back{back_ext}")
        with open(front_path, "wb") as f:
            f.write(front_content)
        with open(back_path, "wb") as f:
            f.write(back_content)
        front_image_path = os.path.join("postcards", str(postcard_id), f"front{front_ext}").replace("\\", "/")
        back_image_path = os.path.join("postcards", str(postcard_id), f"back{back_ext}").replace("\\", "/")

    video_s3_url = None
    video_thumbnail_path = None
    if front_file.content_type and front_file.content_type.startswith("video/"):
        video_s3_url = front_image_path
        thumb_png = extract_video_thumbnail_frame(front_content, front_file.content_type)
        if thumb_png and settings.use_s3:
            thumb_key = f"postcards/{postcard_id}/video_thumbnail.png"
            try:
                video_thumbnail_path = upload_to_s3(
                    key=thumb_key,
                    body=thumb_png,
                    content_type="image/png",
                )
            except Exception as e:
                logger.warning("Failed to upload video thumbnail to S3: %s", e)
        elif thumb_png and not settings.use_s3:
            base_dir = os.path.join(settings.UPLOAD_DIR, "postcards", str(postcard_id))
            _ensure_upload_dir(base_dir)
            thumb_path = os.path.join(base_dir, "video_thumbnail.png")
            with open(thumb_path, "wb") as f:
                f.write(thumb_png)
            video_thumbnail_path = os.path.join("postcards", str(postcard_id), "video_thumbnail.png").replace("\\", "/")

    obj_in = {
        "id": postcard_id,
        "user_id": user_id,
        "receiver_contact_id": receiver_contact_id,
        "front_image_path": front_image_path,
        "back_image_path": back_image_path,
        "personal_message": payload.personal_message,
        "qr_code_data": payload.qr_code_data,
        "design_metadata": payload.design_metadata,
        "image_metadata": image_metadata,
    }
    if video_s3_url is not None:
        obj_in["video_s3_url"] = video_s3_url
    if video_thumbnail_path is not None:
        obj_in["video_thumbnail_path"] = video_thumbnail_path
    postcard = postcard_crud.create_from_dict(db, obj_in=obj_in)
    return PostcardCreateResponse(message="Postcard sent successfully", postcard=postcard)


@router.get("", response_model=PostcardListResponse)
async def list_postcards(
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 10,
):
    """List postcards for the current user with simple pagination (newest first). Requires Bearer token."""
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 10
    user_id = uuid.UUID(current_user["user_id"])
    items, total = postcard_crud.list_by_user_paginated(db, user_id=user_id, page=page, limit=limit)
    total_pages = (total + limit - 1) // limit if total else 0
    return PostcardListResponse(
        items=[PostcardListItem.model_validate(p) for p in items],
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
    )


@router.get("/{postcard_id}", response_model=PostcardResponse)
async def get_postcard(
    postcard_id: uuid.UUID,
    current_user: Dict[str, Any] = Depends(validate_session),
    db: Session = Depends(get_db),
):
    """Get a single postcard by id (must belong to current user). Requires Bearer token."""
    user_id = uuid.UUID(current_user["user_id"])
    postcard = postcard_crud.get_by_user_and_id(db, user_id=user_id, postcard_id=postcard_id)
    if not postcard:
        raise NotFound("Postcard")
    return postcard
