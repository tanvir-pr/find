from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CommissionBasis


class CommissionRuleCreate(BaseModel):
    user_id: UUID
    name: str = Field(min_length=1, max_length=120)
    basis: CommissionBasis
    rate: Decimal = Field(gt=0)


class CommissionRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    basis: CommissionBasis
    rate: Decimal
    is_active: bool


class CommissionEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    rule_id: UUID
    user_id: UUID
    sale_id: UUID
    amount: Decimal
    created_at: datetime
