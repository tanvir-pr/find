"""Seed admin + staff users (Step 3). Idempotent by email."""

import asyncio

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User

SEED_USERS = [
    {
        "name": "Shop Owner",
        "email": "admin@dokan.example",
        "password": "Admin123!",
        "role": UserRole.admin,
    },
    {
        "name": "Cashier Rahim",
        "email": "staff@dokan.example",
        "password": "Staff123!",
        "role": UserRole.staff,
    },
]


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for item in SEED_USERS:
            existing = await session.scalar(select(User).where(User.email == item["email"]))
            if existing:
                print(f"skip {item['email']} (exists, role={existing.role.value})")
                continue
            user = User(
                name=item["name"],
                email=item["email"],
                password_hash=hash_password(item["password"]),
                role=item["role"],
                is_active=True,
            )
            session.add(user)
            print(f"created {item['email']} role={item['role'].value}")
        await session.commit()
    print("seed_users done")


if __name__ == "__main__":
    asyncio.run(main())
