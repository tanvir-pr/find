from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SyncStatus
from app.models.system import SyncLog
from app.models.user import User
from app.modules.sales.service import create_sale
from app.modules.sync.schemas import SyncSaleResult, SyncSalesRequest, SyncSalesResponse


async def sync_offline_sales(
    session: AsyncSession, user: User, data: SyncSalesRequest
) -> SyncSalesResponse:
    results: list[SyncSaleResult] = []
    for item in data.items:
        existing = await session.scalar(
            select(SyncLog).where(
                SyncLog.device_id == item.device_id,
                SyncLog.entity_type == "sale",
                SyncLog.entity_id == item.client_id,
                SyncLog.status == SyncStatus.synced,
            )
        )
        if existing and existing.payload and existing.payload.get("sale_id"):
            results.append(
                SyncSaleResult(client_id=item.client_id, status="already_synced", sale=None)
            )
            continue
        try:
            # Ensure device_id on sale payload
            sale_body = item.sale.model_copy(update={"device_id": item.device_id or data.device_id})
            sale = await create_sale(session, user, sale_body)
            log = SyncLog(
                device_id=item.device_id or data.device_id,
                entity_type="sale",
                entity_id=item.client_id,
                status=SyncStatus.synced,
                payload={"sale_id": str(sale.id), "bill_no": sale.bill_no},
                synced_at=datetime.now(timezone.utc),
            )
            session.add(log)
            await session.commit()
            results.append(SyncSaleResult(client_id=item.client_id, status="synced", sale=sale))
        except Exception as exc:  # noqa: BLE001 — report per-item
            session.add(
                SyncLog(
                    device_id=item.device_id or data.device_id,
                    entity_type="sale",
                    entity_id=item.client_id,
                    status=SyncStatus.conflict,
                    payload=item.sale.model_dump(mode="json"),
                    error_message=str(exc)[:500],
                )
            )
            await session.commit()
            results.append(
                SyncSaleResult(client_id=item.client_id, status="conflict", error=str(exc)[:300])
            )
    return SyncSalesResponse(results=results)
