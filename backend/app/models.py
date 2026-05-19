import aiosqlite
import os

DB_PATH = os.getenv("DB_PATH", "./recruitment.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # used chatgpt for create table scrips
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          TEXT PRIMARY KEY,
                email       TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'reviewer',
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS candidates (
                id             TEXT PRIMARY KEY,
                name           TEXT NOT NULL,
                email          TEXT UNIQUE NOT NULL,
                role_applied   TEXT NOT NULL,
                status         TEXT NOT NULL DEFAULT 'new',
                skills         TEXT NOT NULL DEFAULT '[]',
                internal_notes TEXT,
                ai_summary     TEXT,
                created_at     TEXT NOT NULL,
                deleted_at     TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_candidates_status      ON candidates(status);
            CREATE INDEX IF NOT EXISTS idx_candidates_role_applied ON candidates(role_applied);

            CREATE TABLE IF NOT EXISTS scores (
                id           TEXT PRIMARY KEY,
                candidate_id TEXT NOT NULL,
                category     TEXT NOT NULL,
                score        INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
                reviewer_id  TEXT NOT NULL,
                note         TEXT,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (candidate_id) REFERENCES candidates(id),
                FOREIGN KEY (reviewer_id)  REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_scores_candidate_id ON scores(candidate_id);
            CREATE INDEX IF NOT EXISTS idx_scores_reviewer_id  ON scores(reviewer_id);
        """)
        await db.commit()

        # Seed default admin
        from app.auth import get_password_hash
        import uuid, json
        from datetime import datetime, timezone

        existing = await db.execute("SELECT id FROM users WHERE email = 'admin@test.com'")
        if not await existing.fetchone():
            admin_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO users (id, email, hashed_password, role, created_at) VALUES (?,?,?,?,?)",
                (admin_id, "admin@test.com", get_password_hash("admin1234"), "admin",
                 datetime.now(timezone.utc).isoformat())
            )
            
        existing = await db.execute("SELECT id FROM users WHERE email = 'reviewer@test.com'")
        if not await existing.fetchone():
            reviewer_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO users (id, email, hashed_password, role, created_at) VALUES (?,?,?,?,?)",
                (reviewer_id, "reviewer@test.com", get_password_hash("reviewer1234"), "reviewer",
                 datetime.now(timezone.utc).isoformat())
            )

        # Seed sample candidates
        existing_c = await db.execute("SELECT id FROM candidates LIMIT 1")
        if not await existing_c.fetchone():
            sample = [
                ("User A", "userA@example.com", "Backend Engineer", "new",
                 json.dumps(["Python", "FastAPI", "PostgreSQL"]), None),
                ("User B", "userB@example.com", "Frontend Engineer", "reviewed",
                 json.dumps(["React", "TypeScript", "CSS"]), "Strong portfolio"),
                ("User C", "userC@example.com", "Full Stack Engineer", "hired",
                 json.dumps(["Python", "React", "Docker"]), "Excellent culture fit"),
                ("User D", "userD@example.com", "DevOps Engineer", "rejected",
                 json.dumps(["Kubernetes", "Terraform", "AWS"]), "Lacks team experience"),
                ("User E", "userE@example.com", "Backend Engineer", "new",
                 json.dumps(["Go", "gRPC", "Redis"]), None),
                ("User F", "userF@example.com", "Full Stack Engineer", "reviewed",
                 json.dumps(["Node.js", "Vue", "MongoDB"]), "Good problem solver"),
            ]
            now = datetime.now(timezone.utc).isoformat()
            for name, email, role, status, skills, notes in sample:
                cid = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO candidates (id, name, email, role_applied, status, skills, internal_notes, created_at) VALUES (?,?,?,?,?,?,?,?)",
                    (cid, name, email, role, status, skills, notes, now)
                )

        await db.commit()