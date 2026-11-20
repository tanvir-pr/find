"""OpenAI-style tool schemas for the 7 read-only assistant tools."""

from __future__ import annotations

from typing import Any

from app.models.enums import UserRole

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": (
                "পণ্যের নাম বা বারকোড দিয়ে বর্তমান স্টক, ভার্সন ও দাম দেখায়। "
                "যেমন: লাল কলম কয়টা আছে?"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "পণ্যের নাম, ভার্সন বা বারকোড",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "low_stock_list",
            "description": "যেসব পণ্যের স্টক থ্রেশহোল্ডের নিচে নেমেছে তার তালিকা।",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "ঐচ্ছিক ক্যাটাগরি ফিল্টার",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "expiring_items",
            "description": "মেয়াদ শেষ হওয়া বা শিগগির শেষ হবে এমন ব্যাচের তালিকা।",
            "parameters": {
                "type": "object",
                "properties": {
                    "within_days": {
                        "type": "integer",
                        "description": "কত দিনের মধ্যে (ডিফল্ট ৩০)",
                        "default": 30,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sales_summary",
            "description": (
                "বিক্রি, লাভ অনুমান, বিল সংখ্যা ও পেমেন্ট মাধ্যম অনুযায়ী সারাংশ। "
                "লাভ তথ্য শুধু admin/manager।"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["today", "week", "month"],
                        "description": "সময়সীমা",
                    },
                    "staff_name": {
                        "type": "string",
                        "description": "ঐচ্ছিক কর্মচারীর নাম ফিল্টার",
                    },
                },
                "required": ["period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reorder_suggestion",
            "description": "গত কয়েক সপ্তাহের গড় বিক্রি ও বর্তমান স্টক দেখে কী কিনতে হবে।",
            "parameters": {
                "type": "object",
                "properties": {
                    "lookback_days": {
                        "type": "integer",
                        "description": "গত কত দিনের বিক্রি দেখবে (ডিফল্ট ২৮)",
                        "default": 28,
                    },
                    "cover_days": {
                        "type": "integer",
                        "description": "কত দিনের জন্য স্টক রাখতে চান (ডিফল্ট ১৪)",
                        "default": 14,
                    },
                    "category": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "seasonal_top_products",
            "description": "মৌসুম বা মাস অনুযায়ী সবচেয়ে বেশি বিক্রি হওয়া পণ্য ও ভার্সন।",
            "parameters": {
                "type": "object",
                "properties": {
                    "season": {
                        "type": "string",
                        "enum": [
                            "winter_start",
                            "winter_end",
                            "summer_start",
                            "summer_end",
                        ],
                        "description": "মৌসুম কোড; না দিলে month ব্যবহার করুন",
                    },
                    "month": {
                        "type": "integer",
                        "description": "১–১২ মাস (season না থাকলে)",
                        "minimum": 1,
                        "maximum": 12,
                    },
                    "category": {"type": "string"},
                    "year": {
                        "type": "integer",
                        "description": "ঐচ্ছিক বছর; না দিলে সিড/সাম্প্রতিক বছর",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "customer_due",
            "description": "কাস্টমারের বাকি, ক্রেডিট লিমিট ও শেষ পেমেন্ট। শুধু admin/manager।",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "নাম বা ফোন; খালি থাকলে সব বাকিদার",
                    },
                },
            },
        },
    },
]

# Tools staff may use if chat is later opened to them
STAFF_ALLOWED_TOOLS = frozenset({"check_stock", "low_stock_list", "expiring_items"})


def tools_for_role(role: UserRole) -> list[dict[str, Any]]:
    if role == UserRole.admin:
        return TOOL_DEFINITIONS
    if role == UserRole.manager:
        return TOOL_DEFINITIONS
    allowed = STAFF_ALLOWED_TOOLS
    return [
        t
        for t in TOOL_DEFINITIONS
        if t["function"]["name"] in allowed
    ]
