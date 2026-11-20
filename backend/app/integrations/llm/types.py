"""Shared LLM message / tool-call types (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatMessage:
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None  # tool name when role=tool


@dataclass
class LLMResponse:
    message: ChatMessage
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None
