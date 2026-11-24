import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentMethod, PaymentType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Sale(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable after save — corrections via returns."""

    __tablename__ = "sales"

    bill_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    # Bill / promo discount only — NOT loyalty points
    discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    # Loyalty: 1 point = ৳1; tracked separately so cash/online still reconcile
    points_discount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    points_redeemed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    customer = relationship("Customer", back_populates="sales")
    user = relationship("User")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="sale")
    returns = relationship("Return", back_populates="sale")


class SaleItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sale_items"

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    sale = relationship("Sale", back_populates="items")
    variant = relationship("ProductVariant")
    batch = relationship("Batch")


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (UniqueConstraint("txn_id", name="uq_payments_txn_id"),)

    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType, name="payment_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    sale_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="SET NULL"),
        index=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id", ondelete="SET NULL"),
        index=True,
    )
    purchase_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_invoices.id", ondelete="SET NULL"),
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    txn_id: Mapped[str | None] = mapped_column(String(120))
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    note: Mapped[str | None] = mapped_column(Text)

    sale = relationship("Sale", back_populates="payments")


class Return(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "returns"

    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sale_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sale_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
    )
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    is_damaged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    sale = relationship("Sale", back_populates="returns")
    sale_item = relationship("SaleItem")
