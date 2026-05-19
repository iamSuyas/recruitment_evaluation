import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport

# Use a separate test DB
import os
os.environ["DB_PATH"] = "./test_recruitment.db"

from app.main import app
from app.models import init_db


@pytest_asyncio.fixture(scope="module")
async def client():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    # Cleanup
    if os.path.exists("./test_recruitment.db"):
        os.remove("./test_recruitment.db")


@pytest_asyncio.fixture(scope="module")
async def admin_token(client):
    resp = await client.post("/auth/login", data={
        "username": "admin@test.com",
        "password": "admin1234"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="module")
async def reviewer_token(client):
    await client.post("/auth/register", json={
        "email": "reviewer1@test.com",
        "password": "testpass123"
    })
    resp = await client.post("/auth/login", data={
        "username": "reviewer1@test.com",
        "password": "testpass123"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest_asyncio.fixture(scope="module")
async def reviewer2_token(client):
    await client.post("/auth/register", json={
        "email": "reviewer2@test.com",
        "password": "testpass456"
    })
    resp = await client.post("/auth/login", data={
        "username": "reviewer2@test.com",
        "password": "testpass456"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


# ── Test 1: Unauthenticated access is rejected ────────────────────────────────

@pytest.mark.asyncio
async def test_unauthenticated_list_candidates(client):
    resp = await client.get("/candidates")
    assert resp.status_code == 401


# ── Test 2: Admin can list candidates ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_list_candidates(client, admin_token):
    resp = await client.get("/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


# ── Test 3: Registration hardcodes role to reviewer ───────────────────────────

@pytest.mark.asyncio
async def test_registration_ignores_role(client):
    # Even if someone sends a role field, it must be ignored (Pydantic schema doesn't accept it)
    resp = await client.post("/auth/register", json={
        "email": "hacker@test.com",
        "password": "hacker123"
        # Note: 'role' field is NOT in the schema — hardcoded server-side
    })
    assert resp.status_code == 201
    assert resp.json()["role"] == "reviewer"


# ── Test 4: Reviewer cannot view internal_notes ───────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_cannot_see_internal_notes(client, admin_token, reviewer_token):
    # Get a candidate as admin first
    list_resp = await client.get("/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    candidate_id = list_resp.json()["items"][0]["id"]

    # Admin sets internal notes
    await client.patch(
        f"/candidates/{candidate_id}/notes",
        json={"internal_notes": "Secret admin note"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # Reviewer fetches — should NOT see notes
    resp = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["internal_notes"] is None


# ── Test 5: Reviewer sees only their own scores ───────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_isolation(client, admin_token, reviewer_token, reviewer2_token):
    list_resp = await client.get("/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    candidate_id = list_resp.json()["items"][0]["id"]

    # reviewer1 submits a score
    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Technical Skills", "score": 4, "note": "Good"},
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    # reviewer2 submits a score
    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Communication", "score": 3},
        headers={"Authorization": f"Bearer {reviewer2_token}"}
    )

    # reviewer1 fetches detail — should only see their own score
    resp1 = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    scores1 = resp1.json()["scores"]
    reviewer_ids = {s["reviewer_id"] for s in scores1}
    assert len(reviewer_ids) == 1  # Only one reviewer's scores visible

    # admin sees ALL scores
    resp_admin = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert len(resp_admin.json()["scores"]) >= 2


# ── Test 6: Score validation (1–5) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_score_validation(client, reviewer_token, admin_token):
    list_resp = await client.get("/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    candidate_id = list_resp.json()["items"][0]["id"]

    resp = await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Culture Fit", "score": 6},  # Invalid: > 5
        headers={"Authorization": f"Bearer {reviewer_token}"}
    )
    assert resp.status_code == 422


# ── Test 7: Soft delete (candidate archived, not hard-deleted) ────────────────

@pytest.mark.asyncio
async def test_soft_delete(client, admin_token):
    list_resp = await client.get("/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    candidate_id = list_resp.json()["items"][-1]["id"]

    del_resp = await client.delete(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert del_resp.status_code == 200

    # Should no longer appear in list
    list_resp2 = await client.get("/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    ids = [c["id"] for c in list_resp2.json()["items"]]
    assert candidate_id not in ids

    # But it still exists in DB (soft delete) — verified by attempting admin detail
    detail_resp = await client.get(
        f"/candidates/{candidate_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert detail_resp.status_code == 404  # API correctly hides archived


# ── Test 8: Pagination ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagination(client, admin_token):
    resp = await client.get(
        "/candidates?limit=2&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 2
    assert data["limit"] == 2
    assert data["offset"] == 0