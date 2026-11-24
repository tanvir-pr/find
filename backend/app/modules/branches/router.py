from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.branch import Branch
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles

router = APIRouter(prefix="/api/v1/branches", tags=["branches"])


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str | None = None
    address: str | None = None
    phone: str | None = None


class BranchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str | None
    address: str | None
    phone: str | None
    is_active: bool


@router.get("", response_model=list[BranchResponse])
async def list_branches(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager, UserRole.staff))],
) -> list[BranchResponse]:
    rows = (await session.scalars(select(Branch).order_by(Branch.name))).all()
    return [
        BranchResponse(
            id=str(b.id),
            name=b.name,
            code=b.code,
            address=b.address,
            phone=b.phone,
            is_active=b.is_active,
        )
        for b in rows
    ]


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    body: BranchCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
) -> BranchResponse:
    branch = Branch(
        name=body.name.strip(),
        code=body.code,
        address=body.address,
        phone=body.phone,
        is_active=True,
    )
    session.add(branch)
    await session.commit()
    await session.refresh(branch)
    return BranchResponse(
        id=str(branch.id),
        name=branch.name,
        code=branch.code,
        address=branch.address,
        phone=branch.phone,
        is_active=branch.is_active,
    )
