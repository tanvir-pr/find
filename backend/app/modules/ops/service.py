"""Daily SMS, offers, CSV import helpers, invoice OCR (Gemini or mock)."""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.integrations.notify import send_sms
from app.models.customer import Customer
from app.models.enums import SmsPurpose
from app.models.product import ProductVariant
from app.models.user import User
from app.modules.ops.schemas import (
    CsvImportLine,
    CsvImportRequest,
    DailySmsResponse,
    OcrInvoiceLine,
    OcrInvoiceRequest,
    OcrInvoiceResponse,
    OfferSendRequest,
    OfferSendResult,
)
from app.modules.reports.service import sales_summary as report_sales_summary
from app.modules.stock.schemas import PurchaseCreate, PurchaseLineCreate
from app.modules.stock.service import create_purchase


async def send_daily_summary_sms(
    session: AsyncSession, user: User, to_phone: str | None = None
) -> DailySmsResponse:
    today = date.today()
    summary = await report_sales_summary(session, today, today)
    phone = (to_phone or "").strip() or "01711001100"

    body = (
        f"Dokan daily: sales ৳{summary.total_sales}, "
        f"points discount ৳{summary.total_points_discount}, "
        f"profit ৳{summary.estimated_profit}, "
        f"bills {summary.bill_count}, cash ৳{summary.cash}, "
        f"bKash ৳{summary.bkash}, Nagad ৳{summary.nagad}, credit ৳{summary.credit}."
    )
    log = await send_sms(
        session,
        purpose=SmsPurpose.daily_summary,
        to_phone=phone,
        body=body,
        meta={"from_date": str(today), "to_date": str(today)},
    )
    await session.commit()
    return DailySmsResponse(sent=True, to_phone=phone, body=body, sms_log_id=log.id)


async def send_offers(session: AsyncSession, data: OfferSendRequest) -> OfferSendResult:
    stmt = select(Customer)
    if data.area:
        stmt = stmt.where(Customer.area == data.area)
    if data.only_opt_in:
        stmt = stmt.where(Customer.offer_opt_in.is_(True))
    customers = (await session.scalars(stmt)).all()
    sent = 0
    skipped = 0
    for c in customers:
        if not c.phone:
            skipped += 1
            continue
        await send_sms(
            session,
            purpose=SmsPurpose.offer,
            to_phone=c.phone,
            body=data.message,
            customer_id=c.id,
            meta={"area": c.area},
        )
        sent += 1
    await session.commit()
    return OfferSendResult(sent_count=sent, skipped=skipped, sample_body=data.message)


async def import_purchase_csv(
    session: AsyncSession, user: User, data: CsvImportRequest
):
    lines: list[PurchaseLineCreate] = []
    for row in data.lines:
        variant = await session.scalar(
            select(ProductVariant).where(ProductVariant.barcode == row.barcode.strip())
        )
        if variant is None:
            raise NotFoundError(f"Barcode not found: {row.barcode}")
        lines.append(
            PurchaseLineCreate(
                variant_id=variant.id,
                qty=row.qty,
                cost_price=row.cost_price,
                expiry_date=row.expiry_date,
            )
        )
    return await create_purchase(
        session,
        PurchaseCreate(
            supplier_id=data.supplier_id,
            invoice_no=data.invoice_no,
            invoice_date=data.invoice_date,
            lines=lines,
        ),
        user,
    )


def _parse_decimal(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    try:
        cleaned = re.sub(r"[^\d.]", "", str(raw))
        return Decimal(cleaned) if cleaned else None
    except (InvalidOperation, ValueError):
        return None


def _mock_ocr_from_text(text: str) -> OcrInvoiceResponse:
    lines: list[OcrInvoiceLine] = []
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        # barcode,qty,cost[,expiry] OR name qty cost
        parts = [p.strip() for p in re.split(r"[,|\t]+", raw) if p.strip()]
        if len(parts) >= 3 and re.match(r"^[A-Za-z0-9\-]+$", parts[0]):
            qty = _parse_decimal(parts[1])
            cost = _parse_decimal(parts[2])
            expiry = None
            if len(parts) >= 4:
                try:
                    expiry = date.fromisoformat(parts[3])
                except ValueError:
                    expiry = None
            lines.append(
                OcrInvoiceLine(
                    name=parts[0],
                    barcode=parts[0],
                    qty=qty,
                    cost_price=cost,
                    expiry_date=expiry,
                )
            )
        elif len(parts) >= 3:
            lines.append(
                OcrInvoiceLine(
                    name=parts[0],
                    qty=_parse_decimal(parts[1]),
                    cost_price=_parse_decimal(parts[2]),
                )
            )
    if not lines:
        lines = [
            OcrInvoiceLine(name="Glue Stick 20g", qty=Decimal("20"), cost_price=Decimal("35")),
            OcrInvoiceLine(name="Ball Pen Red", qty=Decimal("100"), cost_price=Decimal("8")),
        ]
    return OcrInvoiceResponse(provider="mock", lines=lines, raw_notes="Parsed locally")


async def ocr_invoice(data: OcrInvoiceRequest) -> OcrInvoiceResponse:
    text = (data.text or "").strip()
    if not text and data.image_base64:
        text = "image_uploaded"
    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        return _mock_ocr_from_text(text if text != "image_uploaded" else "")

    prompt = (
        "Extract purchase invoice lines as JSON array with keys: "
        "name, qty, cost_price, barcode, expiry_date (YYYY-MM-DD or null). "
        "Return ONLY JSON.\n\nInvoice text:\n"
        + (text if text != "image_uploaded" else "(image provided; invent nothing — return [])")
    )
    payload = {
        "model": settings.LLM_MODEL or "gemini-3.5-flash",
        "messages": [{"role": "user", "content": prompt}],
    }
    url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        if resp.status_code >= 400:
            return _mock_ocr_from_text(text)
        content = resp.json()["choices"][0]["message"]["content"] or "[]"
        match = re.search(r"\[.*\]", content, re.S)
        raw_list = json.loads(match.group(0) if match else content)
        lines = []
        for item in raw_list:
            expiry = item.get("expiry_date")
            exp = date.fromisoformat(expiry) if expiry else None
            lines.append(
                OcrInvoiceLine(
                    name=str(item.get("name") or "item"),
                    qty=_parse_decimal(str(item.get("qty"))) if item.get("qty") is not None else None,
                    cost_price=_parse_decimal(str(item.get("cost_price")))
                    if item.get("cost_price") is not None
                    else None,
                    barcode=item.get("barcode"),
                    expiry_date=exp,
                )
            )
        return OcrInvoiceResponse(provider="openai_compatible", lines=lines or _mock_ocr_from_text(text).lines)
    except Exception:
        return _mock_ocr_from_text(text)


def parse_csv_text(csv_text: str) -> list[CsvImportLine]:
    lines: list[CsvImportLine] = []
    for i, raw in enumerate(csv_text.splitlines()):
        raw = raw.strip()
        if not raw or raw.lower().startswith("barcode"):
            continue
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 3:
            raise BusinessRuleError(f"Bad CSV line {i + 1}: need barcode,qty,cost")
        expiry = None
        if len(parts) >= 4 and parts[3]:
            expiry = date.fromisoformat(parts[3])
        lines.append(
            CsvImportLine(
                barcode=parts[0],
                qty=Decimal(parts[1]),
                cost_price=Decimal(parts[2]),
                expiry_date=expiry,
            )
        )
    if not lines:
        raise BusinessRuleError("CSV has no data rows")
    return lines
