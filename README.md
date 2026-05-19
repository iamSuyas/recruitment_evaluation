# Recruitment Dashboard

An internal candidate scoring and review dashboard.



## Stack

| Layer    | Technology                       |
|----------|----------------------------------|
| Backend  | Python 3.12 + FastAPI + aiosqlite |
| Frontend | React 18 + Vite (port 5173)      |
| Auth     | JWT (python-jose + passlib/bcrypt) |
| DB       | SQLite (via aiosqlite, async)    |
| Infra    | Docker Compose                   |



## Setup & Run

### Prerequisites

- Docker + Docker Compose

### 1. Clone and configure environment

```bash
git clone https://github.com/iamSuyas/recruitment_evaluation.git
cd recruitment_evaluation
cp .env.example .env
# Edit .env and set a strong SECRET_KEY
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

| Service  | URL                         |
|----------|-----------------------------|
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API Docs | http://localhost:8000/docs  |

### 3. Default credentials (seeded on first boot)

| Role     | Email                    | Password   |
|----------|--------------------------|------------|
| Admin    | admin@test.com      | admin1234  |
| Reviewer    | reviewer@test.com      | reviewer1234  |

Reviewer accounts can be registered via `POST /auth/register`.



## Running Tests

```bash
cd backend
pip install -r requirements.txt
pytest tests/ -v
```



## Example API Calls

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@test.com&password=admin1234" \
  -H "Content-Type: application/x-www-form-urlencoded"

# Set TOKEN from response
TOKEN=<access_token>

# List candidates (with filters)
curl http://localhost:8000/candidates?status=new&limit=5 \
  -H "Authorization: Bearer $TOKEN"

# Get candidate detail
curl http://localhost:8000/candidates/<id> \
  -H "Authorization: Bearer $TOKEN"

# Submit a score
curl -X POST http://localhost:8000/candidates/<id>/scores \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"category": "Technical Skills", "score": 4, "note": "Strong fundamentals"}'

# Trigger AI summary (takes ~2s)
curl -X POST http://localhost:8000/candidates/<id>/summary \
  -H "Authorization: Bearer $TOKEN"

# Register a new reviewer
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "reviewer@example.com", "password": "securepass"}'

# Update internal notes (admin only)
curl -X PATCH http://localhost:8000/candidates/<id>/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"internal_notes": "Strong candidate, fast-track to final round"}'

# Soft-delete (archive) a candidate
curl -X DELETE http://localhost:8000/candidates/<id> \
  -H "Authorization: Bearer $TOKEN"

# Stream score updates (SSE, stretch goal)
curl -N http://localhost:8000/candidates/<id>/stream \
  -H "Authorization: Bearer $TOKEN"
```


## Architecture Decision Records (ADR)

### 1) SQLite over DynamoDB-style store

**Context:** The spec says "DynamoDB-style or SQLite." A real DynamoDB would require AWS credentials and add operational overhead.

**Decision:** Use SQLite via `aiosqlite` for fully async I/O without blocking FastAPI's event loop.

**Trade-offs:**
- Zero external dependencies; runs entirely in Docker
- Supports real SQL indexes (`idx_candidates_status`, `idx_scores_candidate_id`)
- Easy to inspect with standard tooling
- Not horizontally scalable; not appropriate for multi-region deployments
- File-locking limits high write concurrency

**Consequence:** For this internal tool with low concurrent writes, SQLite is appropriate. In production, swap to PostgreSQL (the `aiosqlite` dependency can be replaced with `asyncpg` with minimal ORM changes).



### 2) JWT Stateless Auth with Hardcoded Reviewer Role on Registration

**Context:** Need role-based access control without adding a Redis session store.

**Decision:** Stateless JWT tokens signed with HS256. The `role` claim is embedded in the token and decoded on every request. Registration **always** sets `role = "reviewer"` server-side — the client cannot inject a role.

**Trade-offs:**
- No session store needed
- Horizontally scalable (any instance can verify the token)
- Role cannot be spoofed at registration (schema doesn't accept `role` field)
- Tokens cannot be revoked before expiry (no blacklist)
- Role changes require re-login to reflect in token

**Consequence:** For an internal tool with a 60-minute token TTL, the lack of revocation is acceptable. A refresh-token flow or Redis blacklist would be the next step.




## Debugging: Bug Identification


```python
# from a hypothetical service layer — what's wrong here?
def search_candidates(status: str, keyword: str, page: int, page_size: int):
    all_candidates = db.execute("SELECT * FROM candidates").fetchall()
    filtered = [c for c in all_candidates if c["status"] == status]
    # ... also filter by keyword in Python ...
    offset = (page - 1) * page_size
    return filtered[offset : offset + page_size]
```

**The Issue:**
The function fetches the entire table into application memory ``(db.execute("SELECT * ...").fetchall())`` and then uses Python to handle filtering and pagination.


## Why It Fails at Scale

* **Memory Crashing:** Loading millions of rows into Python's RAM on every request will trigger Out-Of-Memory (OOM) crashes.
* **Network Slower:** Transferring the whole database over the wire for a 20-row page saturates network bandwidth.
* **Wasted CPU:** Databases are highly optimized to filter and slice data; doing it in Python app code is slow and expensive.

## The Correct Approach

Push the filtering and pagination workloads to the database layer using `WHERE`, `LIMIT`, and `OFFSET`. This ensures only the requested slice of data travels over the network.

```python
def search_candidates(status: str, keyword: str, page: int, page_size: int):
    offset = (page - 1) * page_size
    
    query = """
        SELECT * FROM candidates
        WHERE status = :status
          AND (bio LIKE :keyword OR skills LIKE :keyword)
        LIMIT :page_size OFFSET :offset
    """
    
    return db.execute(
        query, 
        {
            "status": status, 
            "keyword": f"%{keyword}%", 
            "page_size": page_size, 
            "offset": offset
        }
    ).fetchall()

```

## Learning Reflection

**What went well:**
- FastAPI's dependency injection makes `get_db` and `get_current_user` composable cleanly — no global state.
- `aiosqlite` integrates naturally into the async lifecycle with the `lifespan` context manager for DB init.
- React Router's `<Navigate>` makes auth-gating routes straightforward without a library.

**What I'd do differently with more time:**
- Add a Pydantic `Settings` class (using `pydantic-settings`) rather than raw `os.getenv()` calls for typed, validated configuration.
- Add a refresh-token endpoint to avoid requiring re-login after 60 minutes.
- Replace the mock AI summary with a real streaming LLM call using Server-Sent Events end-to-end (the SSE infrastructure is already in place).
- Add frontend tests with Vitest + React Testing Library.

**Tool use acknowledgment:**
Claude was used to accelerate boilerplate generation and cross-check RBAC logic. All generated code was reviewed, tested, and understood before inclusion. The ADRs, test cases, and architectural decisions reflect genuine reasoning about the problem.



## Limitations Acknowledged

- **SQLite concurrency:** Write-heavy concurrent load may hit SQLite locking. Mitigated for this use case (internal tool, low concurrency).
- **No token revocation:** Logged-out tokens remain valid until expiry (60 min). Acceptable for internal tooling.
- **SSE stream is simplified:** The stretch-goal `/stream` endpoint sends current scores once then keeps the connection alive with comments. A production implementation would use a pub/sub mechanism (e.g., Redis pub/sub) to push real-time updates.
- **No email validation beyond format:** Registration accepts any valid email format.