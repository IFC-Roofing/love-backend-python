"""
Postcard model.
Stores front/back image paths, message, QR data, and design/image metadata for exact replication.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class Postcard(Base):
    __tablename__ = "postcards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)

    front_image_path = Column(String, nullable=False)
    back_image_path = Column(String, nullable=False)
    personal_message = Column(Text, nullable=True)
    qr_code_data = Column(String, nullable=True)

    # Video postcards (DMM does not support video): thumbnail + QR pointing to direct S3 video URL
    video_s3_url = Column(String, nullable=True)
    video_thumbnail_path = Column(String, nullable=True)
    video_qr_image_path = Column(String, nullable=True)

    # Originality: font color, font size, positions, etc. so frontend can replicate exactly
    design_metadata = Column(JSONB, nullable=True)
    # Technical image details (width, height, format, size_kb) per image
    image_metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="postcards")
    receiver_contact = relationship("Contact", backref="postcards_received")
