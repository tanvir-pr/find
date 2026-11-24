from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.modules.auth.deps import require_roles
from app.modules.ops import service
from app.modules.ops.schemas import (
    CsvImportRequest,
    DailySmsResponse,
    OcrInvoiceRequest,
    OcrInvoiceResponse,
    OfferSendRequest,
    OfferSendResult,
)
from app.modules.stock.schemas import PurchaseResponse

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


@router.post("/sms/daily-summary", response_model=DailySmsResponse)
async def daily_summary_sms(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
    to_phone: str | None = None,
) -> DailySmsResponse:
    return await service.send_daily_summary_sms(session, user, to_phone)


@router.post("/sms/offers", response_model=OfferSendResult)
async def send_offers(
    body: OfferSendRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> OfferSendResult:
    return await service.send_offers(session, body)


@router.post("/purchases/import-csv", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def import_csv(
    body: CsvImportRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> PurchaseResponse:
    try:
        return await service.import_purchase_csv(session, user, body)
    except Exception as exc:  # surface unexpected errors for ops tooling
        from app.core.errors import AppError

        if isinstance(exc, AppError):
            raise
        raise AppError(f"CSV import failed: {exc}", status_code=500, code="csv_import_error") from exc


@router.post("/purchases/import-csv-file", response_model=PurchaseResponse, status_code=status.HTTP_201_CREATED)
async def import_csv_file(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
    supplier_id: Annotated[UUID, Form()],
    invoice_no: Annotated[str, Form()],
    invoice_date: Annotated[str, Form()],
    file: UploadFile = File(...),
) -> PurchaseResponse:
    raw = (await file.read()).decode("utf-8", errors="ignore")
    lines = service.parse_csv_text(raw)
    return await service.import_purchase_csv(
        session,
        user,
        CsvImportRequest(
            supplier_id=supplier_id,
            invoice_no=invoice_no,
            invoice_date=date.fromisoformat(invoice_date),
            lines=lines,
        ),
    )


@router.post("/invoices/ocr", response_model=OcrInvoiceResponse)
async def invoice_ocr(
    body: OcrInvoiceRequest,
    _: Annotated[User, Depends(require_roles(UserRole.admin, UserRole.manager))],
) -> OcrInvoiceResponse:
    return await service.ocr_invoice(body)
