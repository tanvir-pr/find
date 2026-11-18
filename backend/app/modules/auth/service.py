from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse


async def register_user(session: AsyncSession, data: RegisterRequest) -> UserResponse:
    existing = await session.scalar(select(User).where(User.email == data.email.lower()))
    if existing:
        raise ConflictError("Email already registered")

    user = User(
        name=data.name.strip(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        role=UserRole.staff,
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse.model_validate(user)


async def login_user(session: AsyncSession, data: LoginRequest) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == data.email.lower()))
    if user is None or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("ইমেইল বা পাসওয়ার্ড ভুল।")
    if not user.is_active:
        raise UnauthorizedError("ইমেইল বা পাসওয়ার্ড ভুল।")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)
