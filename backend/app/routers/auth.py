import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.models import get_db
from app.schemas import UserRegister, Token
from app.auth import get_password_hash, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db=Depends(get_db)):
    row = await db.execute("SELECT id FROM users WHERE email = ?", (body.email,))
    if await row.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    # Role is ALWAYS hardcoded to reviewer on registration — never from client
    await db.execute(
        "INSERT INTO users (id, email, hashed_password, role, created_at) VALUES (?,?,?,?,?)",
        (user_id, body.email, get_password_hash(body.password), "reviewer",
         datetime.now(timezone.utc).isoformat())
    )
    await db.commit()
    return {"id": user_id, "email": body.email, "role": "reviewer"}


@router.post("/login", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    row = await db.execute(
        "SELECT id, email, hashed_password, role FROM users WHERE email = ?",
        (form.username,)
    )
    user = await row.fetchone()
    if not user or not verify_password(form.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user["id"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}