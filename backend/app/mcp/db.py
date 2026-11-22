"""DB session + admin actor for MCP tool/resource calls."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User 


@asynccontextmanager
async def mcp_session() -> AsyncIterator[tuple[AsyncSession, User]]:
    async with AsyncSessionLocal() as session:
        user = await session.scalar(
            select(User).where(User.role == UserRole.admin, User.is_active.is_(True)).limit(1)
        )
        if user is None:
            raise RuntimeError("No active admin user — run seed_users / seed_demo first")
        yield session, user
