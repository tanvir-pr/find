import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StockMovementType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class StockMovement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Insert-only source of truth for stock. Never update/delete rows in app logic."""

    __tablename__ = "stock_movements"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        index=True,
    )
    movement_type: Mapped[StockMovementType] = mapped_column(
        Enum(
            StockMovementType,
            name="stock_movement_type",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    ref_type: Mapped[str | None] = mapped_column(String(40))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shifts.id", ondelete="SET NULL"),
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
    )
    device_id: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)

    variant = relationship("ProductVariant")
    batch = relationship("Batch")


class StockCount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_counts"

    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("branches.id", ondelete="SET NULL"),
    )
    counted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    note: Mapped[str | None] = mapped_column(Text)

    lines = relationship("StockCountLine", back_populates="stock_count", cascade="all, delete-orphan")


class StockCountLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stock_count_lines"

    stock_count_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stock_counts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    system_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    counted_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)

    stock_count = relationship("StockCount", back_populates="lines")
