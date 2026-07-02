"""
Agent Memory Service — structured per-user memory that persists across sessions.
Makes the AI feel like it knows you.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.mcp_models import AgentMemory

logger = logging.getLogger("app.services.agent_memory")


def get_memory(user_id: int, db: Session) -> Optional[AgentMemory]:
    """Retrieves or creates agent memory for a user."""
    mem = db.query(AgentMemory).filter(AgentMemory.user_id == user_id).first()
    if not mem:
        mem = AgentMemory(user_id=user_id)
        db.add(mem)
        db.commit()
        db.refresh(mem)
    return mem


def build_context(memory: Optional[AgentMemory]) -> str:
    """Formats memory into a system-prompt string injected into every AI call."""
    if not memory:
        return ""
    parts = []
    if memory.career_goal:
        parts.append(f"Career Goal: {memory.career_goal}")
    if memory.preferred_role:
        parts.append(f"Target Role: {memory.preferred_role}")
    if memory.strong_skills:
        try:
            skills = json.loads(memory.strong_skills)
            if skills:
                parts.append(f"Strong Skills: {', '.join(skills[:8])}")
        except Exception:
            parts.append(f"Strong Skills: {memory.strong_skills}")
    if memory.weak_skills:
        try:
            skills = json.loads(memory.weak_skills)
            if skills:
                parts.append(f"Skills to Improve: {', '.join(skills[:6])}")
        except Exception:
            parts.append(f"Skills to Improve: {memory.weak_skills}")
    if memory.learning_style:
        parts.append(f"Learning Style: {memory.learning_style}")
    if memory.location_preference:
        parts.append(f"Location Preference: {memory.location_preference}")
    if memory.salary_expectation:
        parts.append(f"Salary Expectation: {memory.salary_expectation}")
    if memory.target_companies:
        try:
            companies = json.loads(memory.target_companies)
            if companies:
                parts.append(f"Target Companies: {', '.join(companies[:5])}")
        except Exception:
            pass
    if memory.last_conversation_summary:
        parts.append(f"Previous Context: {memory.last_conversation_summary}")
    if not parts:
        return ""
    return "[User Memory]\n" + "\n".join(parts) + "\n[End Memory]"


def update(user_id: int, message: str, ai_response: str, db: Session):
    """Extracts career signals from a conversation and updates memory."""
    try:
        from app.services.orchestrator import call_gemini
        extract_prompt = f"""Analyze this conversation and extract career information.
Return ONLY valid JSON, no other text:
{{
  "career_goal": "string or null",
  "preferred_role": "string or null",
  "strong_skills": ["skill1", "skill2"],
  "weak_skills": ["skill1", "skill2"],
  "learning_style": "visual|hands-on|reading|null",
  "location_preference": "string or null",
  "salary_expectation": "string or null",
  "target_companies": ["company1", "company2"],
  "conversation_summary": "1-2 sentence summary of what was discussed"
}}

User message: {message[:500]}
AI response: {ai_response[:500]}
"""
        result_str = call_gemini(extract_prompt, json_mode=True)
        if not result_str:
            return
        signals = json.loads(result_str)
        mem = get_memory(user_id, db)
        # Only update non-null signals
        if signals.get("career_goal"):
            mem.career_goal = signals["career_goal"]
        if signals.get("preferred_role"):
            mem.preferred_role = signals["preferred_role"]
        if signals.get("strong_skills"):
            existing = json.loads(mem.strong_skills or "[]")
            merged = list(set(existing + signals["strong_skills"]))[:15]
            mem.strong_skills = json.dumps(merged)
        if signals.get("weak_skills"):
            existing = json.loads(mem.weak_skills or "[]")
            merged = list(set(existing + signals["weak_skills"]))[:10]
            mem.weak_skills = json.dumps(merged)
        if signals.get("learning_style") and signals["learning_style"] != "null":
            mem.learning_style = signals["learning_style"]
        if signals.get("location_preference"):
            mem.location_preference = signals["location_preference"]
        if signals.get("salary_expectation"):
            mem.salary_expectation = signals["salary_expectation"]
        if signals.get("target_companies"):
            existing = json.loads(mem.target_companies or "[]")
            merged = list(set(existing + signals["target_companies"]))[:10]
            mem.target_companies = json.dumps(merged)
        if signals.get("conversation_summary"):
            # Rolling summary: prepend new, keep under 500 chars
            new_summary = signals["conversation_summary"]
            old_summary = mem.last_conversation_summary or ""
            combined = f"{new_summary}. {old_summary}"
            mem.last_conversation_summary = combined[:500]
        mem.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Memory updated for user_id={user_id}")
    except Exception as e:
        logger.error(f"Memory update failed for user_id={user_id}: {e}")
