async def test_list_returns_only_active(client, auth_headers, seeded_db):
    response = await client.get("/api/candidates", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(c["status"] == "Active" for c in data)


async def test_list_excludes_archived(client, auth_headers, seeded_db):
    response = await client.get("/api/candidates", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    ids = [c["id"] for c in data]
    statuses = [c["status"] for c in data]
    assert "cv_t99" not in ids
    assert "Archived" not in statuses


async def test_list_experience_sorted_desc(client, auth_headers, seeded_db):
    response = await client.get("/api/candidates", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    alice = next(c for c in data if c["id"] == "cv_t01")
    assert alice["experience"][0]["startYear"] == 2022
    assert alice["experience"][1]["startYear"] == 2020


async def test_detail_returns_full_profile(client, auth_headers, seeded_db):
    response = await client.get("/api/candidates/cv_t01", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    for key in ("id", "fullName", "headline", "status", "contact", "summary",
                "skills", "experience", "education", "certifications", "languages", "sourceCv"):
        assert key in data, f"missing key: {key}"
    assert "email" in data["contact"]
    assert "fileName" in data["sourceCv"]
    assert "format" in data["sourceCv"]
    assert "path" in data["sourceCv"]
    assert len(data["skills"]) >= 1
    assert len(data["languages"]) >= 1


async def test_detail_archived_returns_200(client, auth_headers, seeded_db):
    response = await client.get("/api/candidates/cv_t99", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "Archived"


async def test_detail_unknown_returns_404(client, auth_headers, seeded_db):
    response = await client.get("/api/candidates/cv_ghost", headers=auth_headers)
    assert response.status_code == 404
    assert "detail" in response.json()


async def test_list_without_auth_returns_401(client):
    response = await client.get("/api/candidates")
    assert response.status_code == 401
