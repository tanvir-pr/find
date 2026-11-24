import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SmsPurpose, SyncStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

# Matches Gemini gemini-embedding-001 with outputDimensionality=768.
EMBEDDING_DIM = 768


class ReceiptLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "receipt_logs"

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    printed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    is_copy: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)


class SmsLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sms_logs"

    purpose: Mapped[SmsPurpose] = mapped_column(
        Enum(SmsPurpose, name="sms_purpose", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    to_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    provider_status: Mapped[str | None] = mapped_column(String(40))
    provider_ref: Mapped[str | None] = mapped_column(String(120))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    meta: Mapped[dict | None] = mapped_column(JSONB)


class EmailLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "email_logs"

    to_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    provider_status: Mapped[str | None] = mapped_column(String(40))
    provider_ref: Mapped[str | None] = mapped_column(String(120))
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    meta: Mapped[dict | None] = mapped_column(JSONB)


class SyncLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sync_logs"

    device_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status", values_callable=lambda x: [e.value for e in x]),
        default=SyncStatus.pending,
        nullable=False,
    )
    payload: Mapped[dict | None] = mapped_column(JSONB)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class KnowledgeChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"

    document_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(EMBEDDING_DIM))
    meta: Mapped[dict | None] = mapped_column(JSONB)
    content_hash: Mapped[str | None] = mapped_column(String(64), index=True)
