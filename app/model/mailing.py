"""
Mailing model.
One record per postcard send to DMM (physical mail).
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class Mailing(Base):
    __tablename__ = "mailings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    postcard_id = Column(UUID(as_uuid=True), ForeignKey("postcards.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)

    recipient_name = Column(String, nullable=True)
    recipient_address = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="pending")
    external_id = Column(String, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    postcard = relationship("Postcard", backref="mailings")
    user = relationship("User", backref="mailings")
    contact = relationship("Contact", backref="mailings")
