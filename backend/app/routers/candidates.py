import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.models import get_db
from app.auth import get_current_user, require_admin
from app.schemas import (
    CandidateListResponse, CandidateOut, CandidateDetail,
    ScoreCreate, ScoreOut, InternalNotesUpdate, SummaryResponse
)
from app.services.candidate_service import generate_ai_summary, build_candidate_filters

router = APIRouter(prefix="/candidates", tags=["candidates"])


def _parse_candidate(row: dict) -> dict:
    d = dict(row)
    if isinstance(d.get("skills"), str):
        try:
            d["skills"] = json.loads(d["skills"])
        except Exception:
            d["skills"] = []
    return d


# List candidates

@router.get("", response_model=CandidateListResponse)
async def list_candidates(
    status_filter: Optional[str] = Query(None, alias="status"),
    role_applied:  Optional[str] = Query(None),
    skill:         Optional[str] = Query(None),
    keyword:       Optional[str] = Query(None),
    offset:        int           = Query(0, ge=0),
    limit:         int           = Query(20, ge=1, le=50),
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    where, params = build_candidate_filters(status_filter, role_applied, skill, keyword)

    count_row = await db.execute(f"SELECT COUNT(*) AS cnt FROM candidates {where}", params)
    total = (await count_row.fetchone())["cnt"]

    rows = await db.execute(
        f"SELECT id,name,email,role_applied,status,skills,created_at FROM candidates {where} "
        f"ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    )
    items = [CandidateOut(**_parse_candidate(r)) for r in await rows.fetchall()]

    return CandidateListResponse(items=items, total=total, offset=offset, limit=limit)


# Candidate detail

@router.get("/{candidate_id}", response_model=CandidateDetail)
async def get_candidate(
    candidate_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await db.execute(
        "SELECT * FROM candidates WHERE id = ? AND deleted_at IS NULL", (candidate_id,)
    )
    cand = await row.fetchone()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    cand_dict = _parse_candidate(cand)

    # Reviewers cannot see internal_notes
    if current_user["role"] != "admin":
        cand_dict["internal_notes"] = None

    # Load scores — reviewers see only their own
    if current_user["role"] == "admin":
        score_rows = await db.execute(
            "SELECT * FROM scores WHERE candidate_id = ? ORDER BY created_at DESC",
            (candidate_id,)
        )
    else:
        score_rows = await db.execute(
            "SELECT * FROM scores WHERE candidate_id = ? AND reviewer_id = ? ORDER BY created_at DESC",
            (candidate_id, current_user["id"])
        )
    scores = [ScoreOut(**dict(r)) for r in await score_rows.fetchall()]
    cand_dict["scores"] = scores

    return CandidateDetail(**cand_dict)


# Submit score

@router.post("/{candidate_id}/scores", response_model=ScoreOut, status_code=status.HTTP_201_CREATED)
async def submit_score(
    candidate_id: str,
    body: ScoreCreate,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await db.execute(
        "SELECT id FROM candidates WHERE id = ? AND deleted_at IS NULL", (candidate_id,)
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Candidate not found")

    score_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        "INSERT INTO scores (id, candidate_id, category, score, reviewer_id, note, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (score_id, candidate_id, body.category, body.score, current_user["id"], body.note, now)
    )
    # Update candidate status to 'reviewed' if still 'new'
    await db.execute(
        "UPDATE candidates SET status = 'reviewed' WHERE id = ? AND status = 'new'",
        (candidate_id,)
    )
    await db.commit()

    return ScoreOut(
        id=score_id, candidate_id=candidate_id, category=body.category,
        score=body.score, reviewer_id=current_user["id"], note=body.note, created_at=now
    )


# AI summary

@router.post("/{candidate_id}/summary", response_model=SummaryResponse)
async def trigger_summary(
    candidate_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await db.execute(
        "SELECT * FROM candidates WHERE id = ? AND deleted_at IS NULL", (candidate_id,)
    )
    cand = await row.fetchone()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    summary = await generate_ai_summary(dict(cand))

    await db.execute(
        "UPDATE candidates SET ai_summary = ? WHERE id = ?", (summary, candidate_id)
    )
    await db.commit()
    return SummaryResponse(summary=summary)


# Update internal notes (admin only)

@router.patch("/{candidate_id}/notes", dependencies=[Depends(require_admin)])
async def update_notes(
    candidate_id: str,
    body: InternalNotesUpdate,
    db=Depends(get_db),
):
    row = await db.execute(
        "SELECT id FROM candidates WHERE id = ? AND deleted_at IS NULL", (candidate_id,)
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Candidate not found")

    await db.execute(
        "UPDATE candidates SET internal_notes = ? WHERE id = ?",
        (body.internal_notes, candidate_id)
    )
    await db.commit()
    return {"detail": "Notes updated"}


# Soft delete (admin only)

@router.delete("/{candidate_id}", dependencies=[Depends(require_admin)])
async def delete_candidate(candidate_id: str, db=Depends(get_db)):
    row = await db.execute(
        "SELECT id FROM candidates WHERE id = ? AND deleted_at IS NULL", (candidate_id,)
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Candidate not found")

    await db.execute(
        "UPDATE candidates SET deleted_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), candidate_id)
    )
    await db.commit()
    return {"detail": "Candidate archived"}


# SSE stream (stretch goal)

@router.get("/{candidate_id}/stream")
async def stream_scores(
    candidate_id: str,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    row = await db.execute(
        "SELECT id FROM candidates WHERE id = ? AND deleted_at IS NULL", (candidate_id,)
    )
    if not await row.fetchone():
        raise HTTPException(status_code=404, detail="Candidate not found")

    async def event_generator():
        last_seen: set[str] = set()
        timeout = 60  # stream for up to 60 seconds
        elapsed = 0
        while elapsed < timeout:
            async with aiosqlite.connect(db._conn._db) if False else _score_query(db, candidate_id, current_user) as score_rows:
                for r in score_rows:
                    if r["id"] not in last_seen:
                        last_seen.add(r["id"])
                        yield f"data: {json.dumps(dict(r))}\n\n"
            await asyncio.sleep(2)
            elapsed += 2

    async def _inner():
        async for chunk in event_generator():
            yield chunk

    # Simplified SSE: push current scores once, then keep-alive
    async def simple_sse():
        if current_user["role"] == "admin":
            rows = await db.execute(
                "SELECT * FROM scores WHERE candidate_id = ? ORDER BY created_at DESC",
                (candidate_id,)
            )
        else:
            rows = await db.execute(
                "SELECT * FROM scores WHERE candidate_id = ? AND reviewer_id = ? ORDER BY created_at DESC",
                (candidate_id, current_user["id"])
            )
        records = await rows.fetchall()
        for r in records:
            yield f"data: {json.dumps(dict(r))}\n\n"
        # Keep alive
        for _ in range(15):
            await asyncio.sleep(2)
            yield ": keep-alive\n\n"

    return StreamingResponse(simple_sse(), media_type="text/event-stream")