"""Route tests for authentication and current-user endpoints."""

from httpx import AsyncClient

_CREDENTIALS = {"email": "alice@example.com", "password": "supersecret1"}


async def _register(client: AsyncClient) -> dict[str, str]:
    response = await client.post("/auth/register", json=_CREDENTIALS)
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_returns_token_pair(client: AsyncClient) -> None:
    body = await _register(client)
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_register_duplicate_email_conflicts(client: AsyncClient) -> None:
    await _register(client)
    response = await client.post("/auth/register", json=_CREDENTIALS)
    assert response.status_code == 409


async def test_login_success_and_failure(client: AsyncClient) -> None:
    await _register(client)

    ok = await client.post("/auth/login", json=_CREDENTIALS)
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/auth/login",
        json={"email": _CREDENTIALS["email"], "password": "wrongpassword"},
    )
    assert bad.status_code == 401


async def test_refresh_rotates_tokens(client: AsyncClient) -> None:
    tokens = await _register(client)
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_refresh_rejects_access_token(client: AsyncClient) -> None:
    tokens = await _register(client)
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["access_token"]}
    )
    assert response.status_code == 401


async def test_get_user_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/user")).status_code == 401


async def test_get_user_returns_profile(client: AsyncClient) -> None:
    tokens = await _register(client)
    response = await client.get(
        "/user", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == _CREDENTIALS["email"]
    assert "id" in body and "created_at" in body
