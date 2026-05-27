async def test_list_returns_only_open(client, auth_headers, seeded_db):
    response = await client.get("/api/positions", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(p["status"] == "Open" for p in data)
    assert all(p["id"] != "pos_t03" for p in data)


async def test_detail_returns_full_position(client, auth_headers, seeded_db):
    response = await client.get("/api/positions/pos_t01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    for key in ("id", "title", "status", "hiringManagerEmail", "description", "sourceDocument"):
        assert key in data, f"missing key: {key}"
    assert isinstance(data["requirements"]["mustHave"], list)


async def test_detail_null_requirements(client, auth_headers, seeded_db):
    response = await client.get("/api/positions/pos_t02", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data.get("requirements") is None


async def test_detail_unknown_returns_404(client, auth_headers, seeded_db):
    response = await client.get("/api/positions/pos_ghost", headers=auth_headers)
    assert response.status_code == 404
    assert "detail" in response.json()


async def test_patch_recruiter_persists(client, recruiter_headers, seeded_db):
    patch_response = await client.patch(
        "/api/positions/pos_t01",
        headers=recruiter_headers,
        json={"title": "Updated Title"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated Title"

    get_response = await client.get("/api/positions/pos_t01", headers=recruiter_headers)
    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Updated Title"


async def test_patch_viewer_returns_403(client, viewer_headers, seeded_db):
    response = await client.patch(
        "/api/positions/pos_t01",
        headers=viewer_headers,
        json={"title": "Should Not Apply"},
    )
    assert response.status_code == 403


async def test_patch_unknown_returns_404(client, recruiter_headers, seeded_db):
    response = await client.patch(
        "/api/positions/pos_ghost",
        headers=recruiter_headers,
        json={"title": "Irrelevant"},
    )
    assert response.status_code == 404


async def test_patch_partial_leaves_other_fields(client, recruiter_headers, seeded_db):
    original = await client.get("/api/positions/pos_t01", headers=recruiter_headers)
    assert original.status_code == 200
    original_data = original.json()
    original_email = original_data["hiringManagerEmail"]
    original_title = original_data["title"]

    patch_response = await client.patch(
        "/api/positions/pos_t01",
        headers=recruiter_headers,
        json={"status": "Closed"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["status"] == "Closed"
    assert patched["hiringManagerEmail"] == original_email
    assert patched["title"] == original_title
