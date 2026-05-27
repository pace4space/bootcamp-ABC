async def test_unauthenticated_returns_401(client):
    response = await client.get("/api/candidates")
    assert response.status_code == 401
    assert "detail" in response.json()


async def test_login_valid_returns_token_and_user(client, seeded_db):
    response = await client.post("/api/auth/login", json={"email": "admin@hellio.com", "password": "admin123"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["token"], str) and data["token"]
    assert data["user"]["email"] == "admin@hellio.com"
    assert data["user"]["role"] == "admin"


async def test_login_wrong_password_returns_401(client, seeded_db):
    response = await client.post("/api/auth/login", json={"email": "admin@hellio.com", "password": "wrong"})
    assert response.status_code == 401


async def test_login_unknown_email_returns_401(client, seeded_db):
    response = await client.post("/api/auth/login", json={"email": "ghost@hellio.com", "password": "admin123"})
    assert response.status_code == 401


async def test_auth_me_returns_current_user(client, auth_headers, seeded_db):
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@hellio.com"
    assert data["role"] == "admin"


async def test_auth_me_without_token_returns_401(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
