"""OpenAI-compatible chat completions client + deterministic mock for offline demos."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import AppError
from app.integrations.llm.types import ChatMessage, LLMResponse, ToolCall


class LLMError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502, code="llm_error")


def _messages_to_openai(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        item: dict[str, Any] = {"role": m.role}
        if m.content is not None:
            item["content"] = m.content
        if m.tool_calls:
            item["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in m.tool_calls
            ]
        if m.tool_call_id:
            item["tool_call_id"] = m.tool_call_id
        if m.name and m.role == "tool":
            item["name"] = m.name
        out.append(item)
    return out


def _parse_tool_calls(raw_calls: list[dict[str, Any]] | None) -> list[ToolCall]:
    if not raw_calls:
        return []
    parsed: list[ToolCall] = []
    for call in raw_calls:
        fn = call.get("function") or {}
        args_raw = fn.get("arguments") or "{}"
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else dict(args_raw)
        except json.JSONDecodeError:
            args = {}
        parsed.append(
            ToolCall(
                id=call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                name=fn.get("name") or "",
                arguments=args if isinstance(args, dict) else {},
            )
        )
    return parsed


class OpenAICompatibleClient:
    """Talks to any OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.LLM_API_KEY).strip()
        self.base_url = (base_url if base_url is not None else settings.LLM_BASE_URL).rstrip("/")
        self.model = (model if model is not None else settings.LLM_MODEL).strip()
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        *,
        tool_choice: str | dict[str, Any] = "auto",
    ) -> LLMResponse:
        if not self.configured:
            raise LLMError("LLM is not configured (set LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": _messages_to_openai(messages),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError("LLM request timed out") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM transport error: {exc}") from exc

        if resp.status_code >= 400:
            raise LLMError(f"LLM error {resp.status_code}: {resp.text[:400]}")

        data = resp.json()
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("Unexpected LLM response shape") from exc

        tool_calls = _parse_tool_calls(msg.get("tool_calls"))
        message = ChatMessage(
            role="assistant",
            content=msg.get("content"),
            tool_calls=tool_calls,
        )
        return LLMResponse(
            message=message,
            finish_reason=choice.get("finish_reason"),
            raw=data,
        )


class MockLLMClient:
    """Keyword → single tool call, then summarize tool JSON. No API key needed."""

    RULES: list[tuple[re.Pattern[str], str, dict[str, Any]]] = [
        (
            re.compile(
                r"ফেরত|রিটার্ন|return|পলিসি|policy|ক্যাশ কম|ক্যাশ ক্লোজ|cash closing|"
                r"\bTIN\b|\bBIN\b|ট্যাক্স|tax|নতুন কাস্টমারকে|ক্রেডিট লিমিট|"
                r"অরিজিনাল|ডুপ্লিকেট.*ফেরত|কোন খাতা|কোন কালি",
                re.I,
            ),
            "search_policy",
            {},
        ),
        (re.compile(r"বাকি|due|credit|করীম|karim|rahima", re.I), "customer_due", {}),
        (re.compile(r"মৌসুম|season|শীত|গরম|winter|summer|জানুয়ার|january", re.I), "seasonal_top_products", {"season": "winter_start"}),
        (re.compile(r"অর্ডার|reorder|কিনতে|order", re.I), "reorder_suggestion", {"cover_days": 14}),
        (re.compile(r"মেয়াদ|expir|ডিসকাউন্ট", re.I), "expiring_items", {"within_days": 30}),
        (re.compile(r"লো.?স্টক|low.?stock|শেষ হয়ে|ফুরিয়ে|order দিতে", re.I), "low_stock_list", {}),
        (re.compile(r"বিক্রি|sales|লাভ|profit|আজ|সারাংশ|summary", re.I), "sales_summary", {"period": "month"}),
        (re.compile(r"স্টক|stock|কয়টা|কতটা|আছে|কলম|ব্যাগ|bag|pen|glue|আঠা", re.I), "check_stock", {"query": "School Bag"}),
    ]

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        *,
        tool_choice: str | dict[str, Any] = "auto",
    ) -> LLMResponse:
        _ = tools, tool_choice
        # If last message is tool result(s), produce a short answer
        if messages and messages[-1].role == "tool":
            tool_bits = [m for m in messages if m.role == "tool"]
            parts = []
            for m in tool_bits[-3:]:
                parts.append(f"{m.name}: {m.content}")
            text = "টুল থেকে পাওয়া তথ্য:\n" + "\n".join(parts)
            return LLMResponse(
                message=ChatMessage(role="assistant", content=text),
                finish_reason="stop",
            )

        user_text = ""
        for m in reversed(messages):
            if m.role == "user" and m.content:
                user_text = m.content
                break

        for pattern, name, args in self.RULES:
            if pattern.search(user_text):
                # Prefer query from user for check_stock
                call_args = dict(args)
                if name == "check_stock":
                    call_args["query"] = user_text.strip()[:80] or "School Bag"
                if name == "search_policy":
                    call_args["query"] = user_text.strip()[:200]
                if name == "customer_due":
                    if re.search(r"karim|করীম|করিম", user_text, re.I):
                        call_args["query"] = "Karim"
                    elif re.search(r"rahima|রহিমা", user_text, re.I):
                        call_args["query"] = "Rahima"
                if name == "seasonal_top_products":
                    if re.search(r"গরম|summer", user_text, re.I):
                        call_args["season"] = "summer_start"
                    elif re.search(r"জানুয়ার|january|শীত", user_text, re.I):
                        call_args["season"] = "winter_start"
                return LLMResponse(
                    message=ChatMessage(
                        role="assistant",
                        content=None,
                        tool_calls=[
                            ToolCall(
                                id=f"mock_{uuid.uuid4().hex[:10]}",
                                name=name,
                                arguments=call_args,
                            )
                        ],
                    ),
                    finish_reason="tool_calls",
                )

        return LLMResponse(
            message=ChatMessage(
                role="assistant",
                content=(
                    "আমি শুধু দোকানের স্টক, বিক্রি, মেয়াদ, বাকি আর পলিসি নিয়ে সাহায্য করতে পারি। "
                    "যেমন: 'লাল কলম কয়টা আছে?', 'আজ কত বিক্রি?', 'কার বাকি আছে?'।"
                ),
            ),
            finish_reason="stop",
        )


def get_llm_client() -> OpenAICompatibleClient | MockLLMClient:
    from app.core.config import get_settings

    s = get_settings()
    real = OpenAICompatibleClient(
        api_key=s.LLM_API_KEY,
        base_url=s.LLM_BASE_URL,
        model=s.LLM_MODEL,
    )
    if real.configured:
        return real
    return MockLLMClient()
