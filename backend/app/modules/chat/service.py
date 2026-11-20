"""Chat orchestration: LLM ↔ tools loop (max rounds)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm import ChatMessage, MockLLMClient, OpenAICompatibleClient, get_llm_client
from app.models.user import User
from app.modules.chat.prompts import SYSTEM_PROMPT
from app.modules.chat.schemas import ChatRequest, ChatResponse, ToolInvocation
from app.modules.chat.tool_defs import tools_for_role
from app.modules.chat.tool_executors import execute_tool

MAX_TOOL_ROUNDS = 4


async def chat(session: AsyncSession, user: User, body: ChatRequest) -> ChatResponse:
    client = get_llm_client()
    provider = "mock" if isinstance(client, MockLLMClient) else "openai_compatible"
    tools = tools_for_role(user.role)

    messages: list[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_PROMPT)]
    for turn in body.history:
        messages.append(ChatMessage(role=turn.role, content=turn.content))
    messages.append(ChatMessage(role="user", content=body.message))

    tools_used: list[ToolInvocation] = []

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.chat(messages, tools=tools)
        assistant = response.message
        messages.append(assistant)

        if not assistant.tool_calls:
            reply = (assistant.content or "").strip() or "উত্তর তৈরি করা যায়নি।"
            return ChatResponse(reply=reply, tools_used=tools_used, provider=provider)

        for call in assistant.tool_calls:
            result = await execute_tool(session, user, call.name, call.arguments)
            tools_used.append(
                ToolInvocation(
                    name=call.name,
                    arguments=call.arguments,
                    result_preview=result[:500],
                )
            )
            messages.append(
                ChatMessage(
                    role="tool",
                    content=result,
                    tool_call_id=call.id,
                    name=call.name,
                )
            )

    # Exhausted rounds — ask model once more without tools
    if isinstance(client, OpenAICompatibleClient):
        final = await client.chat(messages, tools=None)
        reply = (final.message.content or "").strip()
    else:
        final = await client.chat(messages, tools=None)
        reply = (final.message.content or "").strip()
    if not reply:
        reply = "টুল চালানো হয়েছে, কিন্তু চূড়ান্ত উত্তর পাওয়া যায়নি। আবার চেষ্টা করুন।"
    return ChatResponse(reply=reply, tools_used=tools_used, provider=provider)
