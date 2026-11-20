from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)


class ToolInvocation(BaseModel):
    name: str
    arguments: dict[str, Any]
    result_preview: str


class ChatResponse(BaseModel):
    reply: str
    tools_used: list[ToolInvocation] = Field(default_factory=list)
    provider: Literal["openai_compatible", "mock"]
