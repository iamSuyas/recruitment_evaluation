import asyncio
import json
import random
from datetime import datetime, timezone


SUMMARY_TEMPLATES = [
    "Candidate demonstrates strong technical proficiency in {skills}. "
    "Their background in {role} roles shows consistent growth. "
    "Communication during the process was clear and professional. "
    "Recommended for next-stage consideration.",

    "Based on the submitted materials, this candidate has solid experience with {skills}. "
    "They appear well-suited for a {role} position. "
    "Reviewers noted attention to detail and structured thinking. "
    "Overall impression is positive.",

    "The candidate's profile for the {role} role highlights expertise in {skills}. "
    "Scores across categories suggest a competent mid-level profile. "
    "Some gaps noted in system design depth, but compensated by practical experience. "
    "Suggest proceeding to technical interview.",
]


async def generate_ai_summary(candidate: dict) -> str:
    """Simulate an async LLM call with a 2-second delay."""
    await asyncio.sleep(2)
    skills = json.loads(candidate["skills"]) if isinstance(candidate["skills"], str) else candidate["skills"]
    skills_str = ", ".join(skills[:3]) if skills else "general software engineering"
    template = random.choice(SUMMARY_TEMPLATES)
    return template.format(skills=skills_str, role=candidate["role_applied"])


def build_candidate_filters(
    status: str | None,
    role_applied: str | None,
    skill: str | None,
    keyword: str | None,
) -> tuple[str, list]:
    conditions = ["deleted_at IS NULL"]
    params: list = []

    if status:
        conditions.append("status = ?")
        params.append(status)
    if role_applied:
        conditions.append("role_applied LIKE ?")
        params.append(f"%{role_applied}%")
    if skill:
        conditions.append("skills LIKE ?")
        params.append(f"%{skill}%")
    if keyword:
        conditions.append("(name LIKE ? OR email LIKE ? OR role_applied LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw, kw])

    where = "WHERE " + " AND ".join(conditions)
    return where, params