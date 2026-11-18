from collections.abc import Callable, Sequence
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError("Missing or invalid authorization token")

    try:
        user_id: UUID = decode_access_token(credentials.credentials)
    except (jwt.PyJWTError, ValueError):
        raise UnauthorizedError("Invalid or expired token") from None

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    allowed: Sequence[UserRole] = roles

    async def _checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise ForbiddenError("You do not have permission for this action")
        return user

    return _checker
