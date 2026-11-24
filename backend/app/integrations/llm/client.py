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
        # Always include content for assistant/tool turns (null when tool-only).
        if m.role in ("assistant", "tool", "system", "user"):
            item["content"] = m.content
        if m.tool_calls:
            serialized: list[dict[str, Any]] = []
            for tc in m.tool_calls:
                entry: dict[str, Any] = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                # Required by Gemini thinking models on the tool-result turn.
                if tc.extra_content:
                    entry["extra_content"] = tc.extra_content
                serialized.append(entry)
            item["tool_calls"] = serialized
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
        extra = call.get("extra_content")
        parsed.append(
            ToolCall(
                id=call.get("id") or f"call_{uuid.uuid4().hex[:12]}",
                name=fn.get("name") or "",
                arguments=args if isinstance(args, dict) else {},
                extra_content=extra if isinstance(extra, dict) else None,
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
        timeout: float = 25.0,
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


def _mock_summarize_tools(tool_bits: list[ChatMessage]) -> str:
    """Turn tool JSON into a short shopkeeper-friendly line (UI also renders cards)."""
    for m in tool_bits[-3:]:
        raw = (m.content or "").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        name = m.name or ""
        if name == "search_policy" and isinstance(data, dict):
            hits = data.get("hits") or []
            if not hits:
                return "এই বিষয়ে দোকানের ডকুমেন্টে স্পষ্ট তথ্য পাইনি। মালিকের সাথে কথা বলুন।"
            blob = " ".join(str(h.get("text") or "") for h in hits if isinstance(h, dict))
            if re.search(r"ডুপ্লিকেট|duplicate", blob, re.I):
                return (
                    "ডুপ্লিকেট ভার্সনের পণ্য সাধারণত ফেরত নেওয়া হয় না। "
                    "শুধু মালিকের অনুমতিতে সমমূল্যে এক্সচেঞ্জ করা যায়।"
                )
            return "দোকানের নিয়ম অনুযায়ী নিচের তথ্য প্রযোজ্য।"
        if name == "sales_summary" and isinstance(data, dict):
            return f"এই সময়ে মোট বিক্রি ৳{data.get('total_sales', '0')} (বিল {data.get('bill_count', 0)}টি)।"
        if name == "check_stock" and isinstance(data, dict):
            n = data.get("count") or len(data.get("matches") or data.get("items") or [])
            return f"স্টক খুঁজে {n}টি মিল পাওয়া গেছে।"
        if name == "low_stock_list" and isinstance(data, dict):
            return f"লো স্টক আইটেম: {data.get('count', 0)}টি।"
        if name == "customer_due" and isinstance(data, dict):
            return f"বাকি সংক্রান্ত ফলাফল: {data.get('count', len(data.get('customers') or []))}টি।"
    return "নিচের কার্ডে তথ্য দেখানো হলো।"


class MockLLMClient:
    """Keyword → single tool call, then summarize tool JSON. No API key needed."""

    RULES: list[tuple[re.Pattern[str], str, dict[str, Any]]] = [
        (
            re.compile(
                r"ফেরত|রিটার্ন|return|take\s*back|exchange|এক্সচেঞ্জ|"
                r"পলিসি|policy|নিয়ম|ক্যাশ কম|ক্যাশ ক্লোজ|cash closing|"
                r"\bTIN\b|\bBIN\b|ট্যাক্স|tax|নতুন কাস্টমারকে|ক্রেডিট লিমিট|"
                r"ডুপ্লিকেট|duplicate|অরিজিনাল|original|"
                r"কোন খাতা|কোন কালি",
                re.I,
            ),
            "search_policy",
            {},
        ),
        (re.compile(r"বাকি|due|credit|করীম|karim|rahima", re.I), "customer_due", {}),
        (re.compile(r"মৌসুম|season|শীত|গরম|winter|summer|জানুয়ার|january", re.I), "seasonal_top_products", {"season": "winter_start"}),
        (re.compile(r"অর্ডার|reorder|কিনতে|\border\b", re.I), "reorder_suggestion", {"cover_days": 14}),
        (re.compile(r"মেয়াদ|expir", re.I), "expiring_items", {"within_days": 30}),
        (re.compile(r"লো.?স্টক|low.?stock|শেষ হয়ে|ফুরিয়ে|running low", re.I), "low_stock_list", {}),
        (
            re.compile(
                r"বিক্রি|বিক্রয়|sales?|sold|sell|লাভ|profit|সারাংশ|summary|"
                r"আজ(?:কে)?|ajke|aajke|\baaj\b|today|total\s+sell",
                re.I,
            ),
            "sales_summary",
            {"period": "today"},
        ),
        # Stock only when clearly asking quantity/availability (not return/policy)
        (
            re.compile(
                r"(স্টক|stock|কয়টা|কতটা|কত\s*আছে|how many|available)|"
                r"((কলম|ব্যাগ|bag|pen|glue|আঠা).*(আছে|কত|stock))|"
                r"((আছে|কত|stock).*(কলম|ব্যাগ|bag|pen|glue|আঠা))",
                re.I,
            ),
            "check_stock",
            {"query": "School Bag"},
        ),
    ]

    async def chat(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]] | None = None,
        *,
        tool_choice: str | dict[str, Any] = "auto",
    ) -> LLMResponse:
        _ = tools, tool_choice
        # If last message is tool result(s), produce a short human answer
        if messages and messages[-1].role == "tool":
            tool_bits = [m for m in messages if m.role == "tool"]
            text = _mock_summarize_tools(tool_bits)
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
                if name == "sales_summary":
                    if re.search(r"মাস|month", user_text, re.I):
                        call_args["period"] = "month"
                    elif re.search(r"সপ্তাহ|week", user_text, re.I):
                        call_args["period"] = "week"
                    else:
                        # আজ / ajke / today / sell → today by default
                        call_args["period"] = "today"
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
