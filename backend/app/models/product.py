import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    unit: Mapped[str] = mapped_column(String(40), default="pcs", nullable=False)
    tracks_expiry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Barcode + low_stock live here (A2 dual price, D4 variants)."""

    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_variant_product_name"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    retail_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    dealer_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    low_stock_threshold: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    product = relationship("Product", back_populates="variants")
    batches = relationship("Batch", back_populates="variant")


class Batch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """initial_qty is purchase reference only — current stock from stock_movements."""

    __tablename__ = "batches"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    purchase_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_invoices.id", ondelete="SET NULL"),
        index=True,
    )
    initial_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)

    variant = relationship("ProductVariant", back_populates="batches")
    purchase_invoice = relationship("PurchaseInvoice", back_populates="batches")
