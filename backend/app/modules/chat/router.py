import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles
from app.modules.chat import service
from app.modules.chat.schemas import ChatRequest, ChatResponse

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> ChatResponse:
    preview = (body.message or "").strip().replace("\n", " ")[:80]
    logger.info("CHAT start user=%s msg=%r", user.email, preview)
    result = await service.chat(session, user, body)
    logger.info(
        "CHAT done provider=%s tools=%s reply_len=%s",
        result.provider,
        [t.name for t in result.tools_used],
        len(result.reply or ""),
    )
    return result
