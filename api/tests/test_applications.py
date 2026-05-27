async def test_list_returns_all_seeded(client, auth_headers, seeded_db):
    response = await client.get("/api/applications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    ids = {a["id"] for a in data}
    assert {"app_t01", "app_t02", "app_t03"} == ids


async def test_list_filter_by_candidate(client, auth_headers, seeded_db):
    response = await client.get("/api/applications?candidateId=cv_t01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(a["candidateId"] == "cv_t01" for a in data)


async def test_list_filter_by_position(client, auth_headers, seeded_db):
    response = await client.get("/api/applications?positionId=pos_t01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(a["positionId"] == "pos_t01" for a in data)


async def test_list_nonexistent_filter_returns_empty(client, auth_headers, seeded_db):
    response = await client.get("/api/applications?candidateId=cv_ghost", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_null_status_serialised(client, auth_headers, seeded_db):
    response = await client.get("/api/applications", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    app_t02 = next(a for a in data if a["id"] == "app_t02")
    assert app_t02["status"] is None


async def test_post_creates_201(client, recruiter_headers, seeded_db):
    response = await client.post(
        "/api/applications",
        headers=recruiter_headers,
        json={"candidateId": "cv_t02", "positionId": "pos_t02"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["candidateId"] == "cv_t02"
    assert data["positionId"] == "pos_t02"
    assert data["status"] is None


async def test_post_persists(client, recruiter_headers, auth_headers, seeded_db):
    await client.post(
        "/api/applications",
        headers=recruiter_headers,
        json={"candidateId": "cv_t02", "positionId": "pos_t02"},
    )
    response = await client.get("/api/applications?candidateId=cv_t02", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    pos_ids = [a["positionId"] for a in data]
    assert "pos_t02" in pos_ids


async def test_post_duplicate_returns_409(client, recruiter_headers, seeded_db):
    response = await client.post(
        "/api/applications",
        headers=recruiter_headers,
        json={"candidateId": "cv_t01", "positionId": "pos_t01"},
    )
    assert response.status_code == 409


async def test_post_unknown_candidate_returns_404(client, recruiter_headers, seeded_db):
    response = await client.post(
        "/api/applications",
        headers=recruiter_headers,
        json={"candidateId": "cv_ghost", "positionId": "pos_t01"},
    )
    assert response.status_code == 404


async def test_post_viewer_returns_403(client, viewer_headers, seeded_db):
    response = await client.post(
        "/api/applications",
        headers=viewer_headers,
        json={"candidateId": "cv_t02", "positionId": "pos_t02"},
    )
    assert response.status_code == 403


async def test_delete_returns_204(client, recruiter_headers, seeded_db):
    response = await client.delete("/api/applications/app_t01", headers=recruiter_headers)
    assert response.status_code == 204
    assert response.content == b""


async def test_delete_persists(client, recruiter_headers, auth_headers, seeded_db):
    await client.delete("/api/applications/app_t01", headers=recruiter_headers)
    response = await client.get("/api/applications", headers=auth_headers)
    assert response.status_code == 200
    ids = [a["id"] for a in response.json()]
    assert "app_t01" not in ids


async def test_delete_unknown_returns_404(client, recruiter_headers, seeded_db):
    response = await client.delete("/api/applications/app_ghost", headers=recruiter_headers)
    assert response.status_code == 404
    assert "detail" in response.json()


async def test_delete_viewer_returns_403(client, viewer_headers, seeded_db):
    response = await client.delete("/api/applications/app_t01", headers=viewer_headers)
    assert response.status_code == 403
