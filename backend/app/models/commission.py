import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CommissionBasis
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CommissionRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commission_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    basis: Mapped[CommissionBasis] = mapped_column(
        Enum(
            CommissionBasis,
            name="commission_basis",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="commission_rules")
    entries = relationship("CommissionEntry", back_populates="rule")


class CommissionEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "commission_entries"

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commission_rules.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sale_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    rule = relationship("CommissionRule", back_populates="entries")
