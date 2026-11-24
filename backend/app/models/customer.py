from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    area: Mapped[str | None] = mapped_column(String(120), index=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, nullable=False)
    offer_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    sales = relationship("Sale", back_populates="customer")
