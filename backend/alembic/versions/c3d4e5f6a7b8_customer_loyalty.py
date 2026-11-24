"""customer email unique + loyalty points

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("loyalty_points", sa.Integer(), nullable=False, server_default="0"),
    )
    # Backfill missing emails so we can enforce NOT NULL + unique
    op.execute(
        """
        UPDATE customers
        SET email = lower('cust.' || regexp_replace(phone, '[^0-9]', '', 'g') || '@dokan.local')
        WHERE email IS NULL OR btrim(email) = ''
        """
    )
    op.execute("UPDATE customers SET email = lower(btrim(email)) WHERE email IS NOT NULL")
    op.alter_column("customers", "email", existing_type=sa.String(length=255), nullable=False)
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_customers_email", table_name="customers")
    op.alter_column("customers", "email", existing_type=sa.String(length=255), nullable=True)
    op.drop_column("customers", "loyalty_points")
