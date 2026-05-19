from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# Auth

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str
    role: str


# Scores

class ScoreCreate(BaseModel):
    category: str = Field(min_length=1, max_length=100)
    score: int = Field(ge=1, le=5)
    note: Optional[str] = None


class ScoreOut(BaseModel):
    id: str
    candidate_id: str
    category: str
    score: int
    reviewer_id: str
    note: Optional[str]
    created_at: str


# Candidates

class CandidateOut(BaseModel):
    id: str
    name: str
    email: str
    role_applied: str
    status: str
    skills: List[str]
    created_at: str


class CandidateDetail(CandidateOut):
    internal_notes: Optional[str]
    ai_summary: Optional[str]
    scores: List[ScoreOut]


class CandidateListResponse(BaseModel):
    items: List[CandidateOut]
    total: int
    offset: int
    limit: int


class InternalNotesUpdate(BaseModel):
    internal_notes: str


class SummaryResponse(BaseModel):
    summary: str