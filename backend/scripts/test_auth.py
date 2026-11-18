"""Quick auth smoke test against running DB."""

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = "test.staff2@example.com"
        password = "Test123!"

        reg = await client.post(
            "/api/v1/auth/register",
            json={"name": "Test Staff 2", "email": email, "password": password},
        )
        print("register", reg.status_code, reg.json())
        assert reg.status_code in (201, 409)

        bad = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong"},
        )
        print("bad_login", bad.status_code, bad.json())
        assert bad.status_code == 401

        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        print("login", login.status_code)
        assert login.status_code == 200
        token = login.json()["access_token"]

        me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        print("me", me.status_code, me.json())
        assert me.status_code == 200
        assert me.json()["role"] == "staff"

        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@dokan.example", "password": "Admin123!"},
        )
        print("admin_login", admin_login.status_code)
        assert admin_login.status_code == 200

        admin_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {admin_login.json()['access_token']}"},
        )
        print("admin_me", admin_me.json()["role"])
        assert admin_me.json()["role"] == "admin"
        print("auth smoke OK")


if __name__ == "__main__":
    asyncio.run(main())
