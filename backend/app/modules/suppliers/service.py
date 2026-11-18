from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier
from app.modules.suppliers.schemas import SupplierCreate, SupplierResponse


async def create_supplier(session: AsyncSession, data: SupplierCreate) -> SupplierResponse:
    supplier = Supplier(name=data.name.strip(), phone=data.phone, address=data.address)
    session.add(supplier)
    await session.commit()
    await session.refresh(supplier)
    return SupplierResponse.model_validate(supplier)


async def list_suppliers(session: AsyncSession) -> list[SupplierResponse]:
    rows = (await session.scalars(select(Supplier).order_by(Supplier.name))).all()
    return [SupplierResponse.model_validate(s) for s in rows]
