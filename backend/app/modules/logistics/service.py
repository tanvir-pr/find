from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.enums import DeliveryStatus
from app.models.logistics import Delivery, Van
from app.modules.logistics.schemas import (
    DeliveryCreate,
    DeliveryResponse,
    DeliveryUpdate,
    VanCreate,
    VanResponse,
)


async def list_vans(session: AsyncSession) -> list[VanResponse]:
    rows = (await session.scalars(select(Van).order_by(Van.name))).all()
    return [VanResponse.model_validate(v) for v in rows]


async def create_van(session: AsyncSession, data: VanCreate) -> VanResponse:
    from sqlalchemy.exc import IntegrityError

    from app.core.errors import ConflictError

    van = Van(
        name=data.name.strip(),
        plate_no=(data.plate_no.strip() if data.plate_no else None),
        driver_name=data.driver_name,
        branch_id=data.branch_id,
        is_active=True,
    )
    session.add(van)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Van plate already exists") from exc
    await session.refresh(van)
    return VanResponse.model_validate(van)


async def list_deliveries(session: AsyncSession) -> list[DeliveryResponse]:
    rows = (await session.scalars(select(Delivery).order_by(Delivery.created_at.desc()).limit(100))).all()
    return [DeliveryResponse.model_validate(d) for d in rows]


async def create_delivery(session: AsyncSession, data: DeliveryCreate) -> DeliveryResponse:
    van = await session.get(Van, data.van_id)
    if van is None:
        raise NotFoundError("Van not found")
    delivery = Delivery(
        van_id=data.van_id,
        customer_id=data.customer_id,
        sale_id=data.sale_id,
        destination=data.destination,
        note=data.note,
        status=DeliveryStatus.pending,
    )
    session.add(delivery)
    await session.commit()
    await session.refresh(delivery)
    return DeliveryResponse.model_validate(delivery)


async def update_delivery(
    session: AsyncSession, delivery_id: UUID, data: DeliveryUpdate
) -> DeliveryResponse:
    delivery = await session.get(Delivery, delivery_id)
    if delivery is None:
        raise NotFoundError("Delivery not found")
    delivery.status = data.status
    if data.note is not None:
        delivery.note = data.note
    now = datetime.now(timezone.utc)
    if data.status == DeliveryStatus.in_transit and delivery.dispatched_at is None:
        delivery.dispatched_at = now
    if data.status == DeliveryStatus.delivered:
        delivery.delivered_at = now
        if delivery.dispatched_at is None:
            delivery.dispatched_at = now
    await session.commit()
    await session.refresh(delivery)
    return DeliveryResponse.model_validate(delivery)
