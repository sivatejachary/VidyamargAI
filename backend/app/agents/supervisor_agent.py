"""
Supervisor Agent — the single routing brain of VidyaMarg AI OS.
Every MCP chat call routes through here.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session
from app.services.orchestrator import call_gemini, call_nvidia
from app.models.mcp_models import AgentMemory, HumanActionItem
from app.schemas.mcp_schemas import ActionCard, HAQCard, MCPChatMessage

logger = logging.getLogger("app.agents.supervisor")

INTENT_LABELS = [
    "job_search", "skill_gap", "resume_improve", "course_recommend",
    "interview_prep", "career_advice", "learning_progress", "general"
]

MODE_SYSTEM_PROMPTS = {
    "resume": """You are Resume AI, an expert ATS resume optimizer and career coach.
Help the candidate improve their resume, increase ATS scores, and stand out.
Be specific, actionable, and encouraging. Reference their actual resume data when available.""",
    "skill-lab": """You are Skill Lab AI, a personalized learning coach.
Help the candidate identify skill gaps, recommend the right courses, and build learning plans.
Connect learning directly to job opportunities — show what skills unlock what roles.""",
    "job-agent": """You are Job Agent AI, an autonomous career intelligence agent.
Help find matching jobs, analyze skill gaps, suggest applications, and track progress.
Be proactive — tell the candidate what to do next to land their target role.""",
    "general": """You are Tush AI, VidyaMarg's intelligent career companion.
Help with anything career-related: jobs, learning, resume, interview prep, salary negotiation.
Be warm, smart, and specific to this candidate's actual situation.""",
}


@dataclass
class SupervisorResult:
    response: str = ""
    action_cards: list = field(default_factory=list)
    haq_required: bool = False
    haq_item: Optional[dict] = None
    memory_updated: bool = False
    intent: str = "general"
    agent_used: str = ""


class SupervisorAgent:
    """
    Routes incoming messages to the correct MCP tools and sub-agents.
    Manages memory, cost, permissions, and action card generation.
    """

    def route(
        self,
        message: str,
        mode: str,
        candidate_id: int,
        user_id: int,
        history: list,
        context_hint: Optional[str],
        db: Session
    ) -> SupervisorResult:
        result = SupervisorResult(agent_used=mode)

        try:
            # 1. Classify intent
            intent = self._classify_intent(message, mode)
            result.intent = intent
            logger.info(f"[Supervisor] user={user_id}, mode={mode}, intent={intent}")

            # Check daily cost budget
            from app.agents.cost_controller import cost_controller
            if not cost_controller.check_budget(user_id, db):
                result.response = "You have reached your daily AI usage budget limit. Please try again tomorrow."
                return result

            # 2. Get agent memory
            from app.services import agent_memory as mem_svc
            memory = mem_svc.get_memory(user_id, db)
            memory_context = mem_svc.build_context(memory)

            # 3. Gather MCP tool context
            tool_context = self._gather_tool_context(intent, mode, candidate_id, db)

            # 4. Build enriched system prompt
            system_prompt = self._build_system_prompt(
                mode, memory_context, tool_context, context_hint
            )

            # 5. Build messages for AI
            messages = [{"role": "user", "content": system_prompt + "\n\nUser: " + message}]
            for h in history[-6:]:  # last 6 messages for context
                messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

            # 6. Call AI (Gemini primary, NVIDIA fallback)
            prompt = f"{system_prompt}\n\nConversation History:\n"
            for h in history[-4:]:
                prompt += f"{h.get('role', 'user').title()}: {h.get('content', '')}\n"
            prompt += f"\nUser: {message}\nAssistant:"

            selected_model = cost_controller.select_model(prompt, user_id, db)
            
            try:
                db.commit() # Commit transaction to avoid idle_in_transaction_session_timeout
            except Exception:
                db.rollback()

            ai_response = None
            model_used = "gemini"

            if selected_model == "gemini":
                ai_response = call_gemini(prompt)
                model_used = "gemini"
            else:
                ai_response = call_nvidia(messages)
                model_used = "nvidia"

            if not ai_response:
                # Try fallback
                if selected_model == "gemini":
                    ai_response = call_nvidia(messages)
                    model_used = "nvidia"
                else:
                    ai_response = call_gemini(prompt)
                    model_used = "gemini"

            if not ai_response:
                ai_response = "I'm having trouble connecting right now. Please try again in a moment."
                model_used = "none"

            result.response = ai_response

            # Record model usage details
            if model_used != "none":
                cost_controller.record(
                    user_id=user_id,
                    model_name=model_used,
                    prompt_chars=len(prompt),
                    completion_chars=len(ai_response),
                    db=db
                )

            # 7. Parse action cards
            try:
                from app.services.action_card_parser import parse_action_cards
                cards = parse_action_cards(ai_response, db, candidate_id, mode)
                result.action_cards = [c.dict() for c in cards]
            except Exception as e:
                logger.error(f"Action card parsing failed: {e}")

            # 8. Update memory async-style (best effort)
            try:
                mem_svc.update(user_id, message, ai_response, db)
                result.memory_updated = True
            except Exception as e:
                logger.error(f"Memory update failed: {e}")

            # 9. Log activity
            try:
                from app.services.agent_activity_feed import log as feed_log
                feed_log(
                    user_id=user_id,
                    agent_name=f"{mode.title()} Agent",
                    action=intent,
                    card_count=len(result.action_cards),
                    meta={"mode": mode, "intent": intent},
                    db=db
                )
            except Exception as e:
                logger.error(f"Activity feed log failed: {e}")

        except Exception as e:
            logger.error(f"[Supervisor] Unhandled error: {e}", exc_info=True)
            result.response = "I encountered an issue. Please try again."

        return result

    def _classify_intent(self, message: str, mode: str) -> str:
        """Classifies user intent. Fast heuristic first, Gemini fallback."""
        msg_lower = message.lower()
        # Heuristic classification
        if any(w in msg_lower for w in ["job", "apply", "hiring", "opening", "position", "role"]):
            return "job_search"
        if any(w in msg_lower for w in ["skill", "gap", "missing", "learn", "course", "study"]):
            if mode == "skill-lab":
                return "course_recommend"
            return "skill_gap"
        if any(w in msg_lower for w in ["resume", "cv", "ats", "score", "improve"]):
            return "resume_improve"
        if any(w in msg_lower for w in ["interview", "prepare", "question", "practice"]):
            return "interview_prep"
        if any(w in msg_lower for w in ["progress", "complete", "finished", "enrolled"]):
            return "learning_progress"
        return "general"

    def _gather_tool_context(self, intent: str, mode: str, candidate_id: int, db: Session) -> str:
        """Calls appropriate services/queries based on intent and mode."""
        ctx_parts = []
        try:
            from app.models.models import Candidate, CandidateProfile, JobMatch, Application, Job
            import json

            if mode == "resume" or intent == "resume_improve":
                profile = db.query(CandidateProfile).filter(
                    CandidateProfile.candidate_id == candidate_id
                ).order_by(CandidateProfile.created_at.desc()).first()
                
                ats_score = "N/A"
                if profile and profile.parsed_metadata:
                    try:
                        meta = json.loads(profile.parsed_metadata)
                        ats_score = meta.get("ats_score", "N/A")
                    except Exception:
                        pass
                
                cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
                if cand:
                    fields = {
                        "summary": cand.summary,
                        "skills": cand.skills,
                        "experience": cand.experience,
                        "education": cand.education,
                        "projects": cand.projects,
                        "phone": cand.phone,
                        "linkedin": cand.linkedin,
                        "github": cand.github,
                    }
                    filled = sum(1 for v in fields.values() if v)
                    total = len(fields)
                    score = round((filled / total) * 100) if total > 0 else 0
                    missing = [k for k, v in fields.items() if not v]
                    
                    ctx_parts.append(f"Resume ATS Score: {ats_score}")
                    ctx_parts.append(f"Profile Completeness: {score}%")
                    if missing:
                        ctx_parts.append(f"Missing: {', '.join(missing)}")

            if mode == "skill-lab" or intent in ["skill_gap", "course_recommend", "learning_progress"]:
                from app.services.learning_health import get_learning_health
                from app.services.skill_gap_graph import get_skill_gaps
                
                health = get_learning_health(candidate_id, db)
                gaps = get_skill_gaps(candidate_id, db)
                
                ctx_parts.append(f"Learning Health: {health.get('health_score', 0)}/100")
                ctx_parts.append(f"Active Courses: {health.get('active_courses', 0)}, Completed: {health.get('completed_courses', 0)}")
                if gaps:
                    top_gaps = [g["skill"] for g in gaps[:5]]
                    ctx_parts.append(f"Top Skill Gaps: {', '.join(top_gaps)}")

            if mode == "job-agent" or intent in ["job_search", "skill_gap"]:
                jobs = db.query(JobMatch, Job).join(
                    Job, JobMatch.job_id == Job.id
                ).filter(
                    JobMatch.candidate_id == candidate_id,
                    Job.status == "active"
                ).order_by(JobMatch.match_score.desc()).limit(20).all()
                
                apps = db.query(Application).filter(Application.candidate_id == candidate_id).count()
                
                ctx_parts.append(f"Matched Jobs Available: {len(jobs)}")
                if jobs:
                    match, job = jobs[0]
                    ctx_parts.append(f"Top Match: {job.title} ({round(match.match_score)}% match)")
                ctx_parts.append(f"Total Applications: {apps}")
                
                # Fetch skill gaps from top matches
                matches = db.query(JobMatch).filter(
                    JobMatch.candidate_id == candidate_id
                ).order_by(JobMatch.match_score.desc()).limit(15).all()
                gap_counts = {}
                for m in matches:
                    if m.skills_gap:
                        for sk in m.skills_gap.split(","):
                            sk = sk.strip().title()
                            if sk:
                                gap_counts[sk] = gap_counts.get(sk, 0) + 1
                gaps_list = sorted(gap_counts.keys(), key=lambda x: gap_counts[x], reverse=True)
                if gaps_list:
                    ctx_parts.append(f"Top Missing Skills for Jobs: {', '.join(gaps_list[:4])}")

        except Exception as e:
            logger.error(f"Tool context gathering failed: {e}")

        return "\n".join(ctx_parts)

    def _build_system_prompt(
        self,
        mode: str,
        memory_context: str,
        tool_context: str,
        context_hint: Optional[str]
    ) -> str:
        base = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS["general"])
        parts = [base]
        if memory_context:
            parts.append(memory_context)
        if tool_context:
            parts.append(f"[Live Data]\n{tool_context}\n[End Data]")
        if context_hint:
            parts.append(f"[Context] {context_hint}")
        parts.append("\nBe concise (3-5 sentences max unless asked for detail). Be specific to this candidate's actual data above. When recommending courses or jobs, mention them by name.")
        return "\n\n".join(parts)


supervisor_agent = SupervisorAgent()
