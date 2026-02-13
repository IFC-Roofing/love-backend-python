"""
Postcard schemas.
"""
from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from pydantic import BaseModel, Field


# --- Design metadata: flexibility for font color, font size, positions, etc.
# Frontend sends a JSON object; we store as-is for exact replication.
DesignMetadataSchema = Dict[str, Any]

# --- Image metadata: extracted by PIL per image.
ImageMetadataSchema = Dict[str, Any]  # e.g. {"front": {...}, "back": {...}}


class PostcardDataIn(BaseModel):
    """JSON body for POST /postcards (sent as 'data' in multipart)."""
    personal_message: Optional[str] = None
    qr_code_data: Optional[str] = None
    design_metadata: Optional[Dict[str, Any]] = None
    receiver_contact_id: Optional[uuid.UUID] = None


class PostcardCreate(BaseModel):
    """Internal create payload (paths + metadata after processing uploads)."""
    id: uuid.UUID
    user_id: uuid.UUID
    front_image_path: str
    back_image_path: str
    personal_message: Optional[str] = None
    qr_code_data: Optional[str] = None
    design_metadata: Optional[Dict[str, Any]] = None
    image_metadata: Optional[Dict[str, Any]] = None


class PostcardResponse(BaseModel):
    """Full postcard for GET by id or single create response."""
    id: uuid.UUID
    user_id: uuid.UUID
    receiver_contact_id: Optional[uuid.UUID] = None
    front_image_path: str
    back_image_path: str
    personal_message: Optional[str] = None
    qr_code_data: Optional[str] = None
    design_metadata: Optional[Dict[str, Any]] = None
    image_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PostcardListItem(BaseModel):
    """Summary for list endpoint."""
    id: uuid.UUID
    user_id: uuid.UUID
    receiver_contact_id: Optional[uuid.UUID] = None
    front_image_path: str
    back_image_path: str
    personal_message: Optional[str] = None
    qr_code_data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PostcardCreateResponse(BaseModel):
    """Response after creating a postcard."""
    message: str = "Postcard sent successfully"
    postcard: PostcardResponse


class PostcardListResponse(BaseModel):
    """Simple page/limit paginated list."""
    items: list[PostcardListItem]
    page: int = Field(..., description="Current page (1-based).")
    limit: int = Field(..., description="Items per page.")
    total: int = Field(..., description="Total number of postcards for this user.")
    total_pages: int = Field(..., description="Total pages (ceil(total / limit)).")
