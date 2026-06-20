from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
import json
import logging
import os
import uuid
import time
import asyncio

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, get_current_admin
from app.schemas import schemas
from app.models.models import *

from app.api.helpers import *
from app.api.helpers import _check_resume_upload_rate_limit, _LIVE_JOB_STORE, _RESUME_UPLOAD_TIMESTAMPS

logger = logging.getLogger(__name__)

router = APIRouter()

# ----------------- AI CAREER COPILOT (NVIDIA/GEMINI) -----------------

@router.post("/chat/copilot", response_model=schemas.ChatCopilotResponse)
async def chat_copilot(
    payload: schemas.ChatCopilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch candidate details
    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    # Check if the user is requesting auto-apply or single-job apply
    lower_message = payload.message.lower()
    auto_apply_triggered = False
    applied_jobs = []
    response_text = ""
    resumes = db.query(CandidateResume).filter(CandidateResume.candidate_id == cand.id).order_by(CandidateResume.uploaded_at.desc()).all()
    
    # 1. Check if "auto apply" or "apply automatically" is requested
    if "auto apply" in lower_message or "apply automatically" in lower_message or "apply to matching jobs" in lower_message or "apply for matching jobs" in lower_message:
        auto_apply_triggered = True
        if resumes:
            latest_resume = resumes[0]
            
            # Fetch dynamic live remote Indian jobs matching candidate skills
            cand_skills = [s.strip().lower() for s in (cand.skills or "").split(",") if s.strip()]
            if not cand_skills:
                cand_skills = ["react", "python", "javascript", "typescript", "node", "sql"]
                
            exp_level = parse_candidate_experience_level(cand)
            raw_jobs = fetch_live_internet_jobs(cand_skills)
            generated_jobs = generate_live_indian_jobs(cand_skills, exp_level)
            
            matched_internet_jobs = []
            for j in raw_jobs:
                loc = j["location"].lower()
                if "india" in loc:
                    title_lower = j["title"].lower()
                    desc_lower = j["description"].lower()
                    tags_lower = [str(t).lower() for t in j["tags"] if t]
                    
                    has_skill = False
                    matched_skills = []
                    for s in cand_skills:
                        if s in title_lower or s in desc_lower or any(s in t for t in tags_lower):
                            has_skill = True
                            matched_skills.append(s.title())
                            
                    if has_skill:
                        matched_internet_jobs.append({
                            "title": j["title"],
                            "company": j["company"],
                            "description": j["description"],
                            "location": j["location"],
                            "tags": matched_skills + [str(t).title() for t in j["tags"] if t and str(t).lower() not in cand_skills],
                            "url": j["url"]
                        })
            
            all_dynamic_jobs = []
            seen = set()
            for j in generated_jobs:
                key = (j["title"].lower(), j["company"].lower())
                if key not in seen:
                    seen.add(key)
                    all_dynamic_jobs.append(j)
            for j in matched_internet_jobs:
                key = (j["title"].lower(), j["company"].lower())
                if key not in seen:
                    seen.add(key)
                    all_dynamic_jobs.append(j)
                    
            # Check already applied jobs to prevent duplicates
            applied_jobs_db = db.query(Job).join(Application).filter(Application.candidate_id == cand.id).all()
            applied_map = { (aj.title.lower(), aj.department.lower()): aj for aj in applied_jobs_db }
            
            import random
            import re
            import html
            
            for idx, j in enumerate(all_dynamic_jobs):
                key = (j["title"].lower(), j["company"].lower())
                if key in applied_map:
                    continue # already applied
                    
                # Match jobs using database profile summary data directly (skills list)
                job_skills = j["tags"]
                
                # Check match level (dynamic jobs are already pre-filtered to match candidate skills, so match_percent is high)
                match_count = 0
                for js in job_skills:
                    js_lower = js.lower()
                    if any(js_lower in cs or cs in js_lower for cs in cand_skills):
                        match_count += 1
                match_percent = (match_count / len(job_skills) * 100) if job_skills else 50
                
                if match_percent >= 40:
                    # Persist this dynamic job to the DB first
                    skills_str = ", ".join(j["tags"][:8])
                    exp = "Senior" if any(k in j["title"].lower() for k in ["senior", "lead", "principal"]) else "Entry-Level" if any(k in j["title"].lower() for k in ["junior", "entry", "intern"]) else "Mid-Level"
                    salary = f"${random.randint(50, 90)}k - ${random.randint(100, 150)}k"
                    
                    desc_clean = re.sub(r'<[^>]*>', '', j["description"])
                    desc_clean = html.unescape(desc_clean).strip()
                    
                    # Persist the job details
                    existing_job = db.query(Job).filter(
                        Job.title == j["title"],
                        Job.department == j["company"]
                    ).first()
                    
                    if not existing_job:
                        db_job = Job(
                            title=j["title"],
                            description=desc_clean,
                            required_skills=skills_str,
                            experience_level=exp,
                            salary_range=salary,
                            location=j["location"],
                            department=j["company"],
                            status="active"
                        )
                        db.add(db_job)
                        db.commit()
                        db.refresh(db_job)
                    else:
                        db_job = existing_job
                        
                    new_app = Application(
                        candidate_id=cand.id,
                        job_id=db_job.id,
                        resume_id=latest_resume.id,
                        status="screening"
                    )
                    db.add(new_app)
                    db.commit()
                    db.refresh(new_app)
                    
                    # Log the agent action
                    await log_agent_action(db, new_app.id, "Auto Apply Agent", "success", f"Automatically matched and applied candidate to Job #{db_job.id} ({db_job.title}) using stored resume summary data.")
                    
                    # Trigger the Screening Agent
                    await orchestrator.run_resume_screening_agent(db, new_app.id)
                    applied_jobs.append(db_job)
                    
            if applied_jobs:
                applied_str = "\n".join([f"- **{j.title}** ({j.location}) - Match Level: High" for j in applied_jobs])
                response_text = (
                    f"### Auto Apply Task Executed Successfully 🚀\n\n"
                    f"I have successfully matched your structured profile against our open jobs and automatically applied you to the following roles:\n\n"
                    f"{applied_str}\n\n"
                    f"Your resume PDF file ({latest_resume.resume_url}) was attached to the applications for verification. "
                    f"The screening process has started. You can track your progress under the **Jobs** tab!"
                )
            else:
                response_text = (
                    "I searched and matched your profile against all active jobs, but did not find any new matching roles where you meet the required skills. "
                    "You have either already applied to all suitable openings or need to update your skills/profile to match other roles."
                )
        else:
            response_text = (
                "It looks like you haven't uploaded a resume yet. "
                "Please navigate to the **Resume Builder** to upload your resume so I can extract your structured summary data and apply automatically!"
            )
            
    # 2. Check if applying to a specific job ID (e.g. "apply to job 2" or "apply to job #2")
    import re
    match_job_request = re.search(r'apply to job (?:id )?#?(\d+)', lower_message)
    if not auto_apply_triggered and match_job_request:
        auto_apply_triggered = True
        job_id = int(match_job_request.group(1))
        
        # Intercept dynamic live jobs (IDs >= 10000) and persist to database on apply
        if job_id >= 10000:
            if job_id not in LIVE_JOBS_CACHE:
                response_text = "The job posting you requested has expired or could not be found. Please refresh the jobs board and try again."
                job = None
            else:
                j_data = LIVE_JOBS_CACHE[job_id]
                
                # Check if already in DB
                existing_job = db.query(Job).filter(
                    Job.title == j_data["title"],
                    Job.department == j_data["department"]
                ).first()
                
                if not existing_job:
                    import random
                    job = Job(
                        title=j_data["title"],
                        description=j_data["description"],
                        required_skills=j_data["required_skills"],
                        experience_level=j_data["experience_level"],
                        salary_range=j_data["salary_range"],
                        location=j_data["location"],
                        department=j_data["department"],
                        status="active"
                    )
                    db.add(job)
                    db.commit()
                    db.refresh(job)
                else:
                    job = existing_job
        else:
            job = db.query(Job).filter(Job.id == job_id, Job.status == "active").first()
        
        if not job and not (auto_apply_triggered and "response_text" in locals() and response_text.startswith("The job posting")):
            response_text = f"I couldn't find an active job with ID #{job_id}. Please check the job openings list and try again."
        elif job:
            if not resumes:
                response_text = (
                    "Please upload your resume in the **Resume Builder** first so I can use your structured profile data to apply."
                )
            else:
                # Check if duplicate application
                existing_app = db.query(Application).filter(Application.candidate_id == cand.id, Application.job_id == job.id).first()
                if existing_app:
                    response_text = f"You have already applied to Job #{job.id} ({job.title}). You can check its status in the Jobs board."
                else:
                    latest_resume = resumes[0]
                    new_app = Application(
                        candidate_id=cand.id,
                        job_id=job.id,
                        resume_id=latest_resume.id,
                        status="screening"
                    )
                    db.add(new_app)
                    db.commit()
                    db.refresh(new_app)
                    
                    # Log agent action
                    await log_agent_action(db, new_app.id, "Auto Apply Agent", "success", f"Automatically applied candidate to Job #{job.id} ({job.title}) on user copilot request.")
                    
                    # Trigger screening agent
                    await orchestrator.run_resume_screening_agent(db, new_app.id)
                    
                    response_text = (
                        f"I have successfully submitted your application for **{job.title}** (Job #{job.id}).\n\n"
                        f"The Screening Agent has started reviewing your profile. You can track this under the **Jobs** tab!"
                    )
                
    if auto_apply_triggered:
        return schemas.ChatCopilotResponse(response=response_text, actions=[{"label": "Browse Job Board", "href": "/candidate/jobs"}])

    # Fetch candidate applications
    apps = db.query(Application).filter(Application.candidate_id == cand.id).all()
    apps_str = ""
    if apps:
        apps_str = "\n".join([
            f"- Job: {a.job.title} (Dept: {a.job.department}), Status: {a.status}, Applied: {a.created_at.strftime('%Y-%m-%d')}"
            for a in apps
        ])
    else:
        apps_str = "No active job applications."

    # Fetch active jobs on the platform (dynamically tailored to candidate's skills)
    cand_skills = [s.strip().lower() for s in (cand.skills or "").split(",") if s.strip()]
    if not cand_skills:
        cand_skills = ["react", "python", "javascript", "typescript", "node", "sql"]
        
    raw_jobs = fetch_live_internet_jobs()
    generated_jobs = generate_live_indian_jobs(cand_skills)
    
    # Filter internet jobs for India + skills
    matched_internet_jobs = []
    for j in raw_jobs:
        loc = j["location"].lower()
        if "india" in loc:
            title_lower = j["title"].lower()
            desc_lower = j["description"].lower()
            tags_lower = [str(t).lower() for t in j["tags"] if t]
            
            has_skill = False
            matched_skills = []
            for s in cand_skills:
                if s in title_lower or s in desc_lower or any(s in t for t in tags_lower):
                    has_skill = True
                    matched_skills.append(s.title())
                    
            if has_skill:
                matched_internet_jobs.append({
                    "title": j["title"],
                    "company": j["company"],
                    "description": j["description"],
                    "location": j["location"],
                    "tags": matched_skills + [str(t).title() for t in j["tags"] if t and str(t).lower() not in cand_skills],
                    "url": j["url"]
                })
                
    # Merge lists
    all_dynamic_jobs = []
    seen = set()
    for j in generated_jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen:
            seen.add(key)
            all_dynamic_jobs.append(j)
    for j in matched_internet_jobs:
        key = (j["title"].lower(), j["company"].lower())
        if key not in seen:
            seen.add(key)
            all_dynamic_jobs.append(j)
            
    # Load candidate's applied jobs from DB to reuse real DB IDs, otherwise map to dynamic IDs
    applied_jobs_db = db.query(Job).join(Application).filter(Application.candidate_id == cand.id).all()
    applied_map = { (aj.title.lower(), aj.department.lower()): aj for aj in applied_jobs_db }
    
    jobs_str = ""
    if all_dynamic_jobs:
        jobs_list_str = []
        for idx, j in enumerate(all_dynamic_jobs[:10]): # present first 10 for AI context to stay clean
            key = (j["title"].lower(), j["company"].lower())
            if key in applied_map:
                jid = applied_map[key].id
            else:
                jid = 10000 + idx
            skills_str = ", ".join(j["tags"][:8])
            jobs_list_str.append(
                f"- Job #{jid}: {j['title']} in {j['location']} (Company: {j['company']}), Required Skills: {skills_str}"
            )
        jobs_str = "\n".join(jobs_list_str)
    else:
        jobs_str = "No open job listings available at the moment."

    # Construct System context prompt
    system_prompt = (
        "You are Baelyx, an autonomous AI Career Copilot on the HireAI platform. Your goal is to guide the candidate, {name}, in their career journey.\n\n"
        "Here is the candidate's real-time profile data:\n"
        "- Name: {name}\n"
        "- Email: {email}\n"
        "- Phone: {phone}\n"
        "- Skills: {skills}\n"
        "- Experience: {experience}\n"
        "- Education: {education}\n\n"
        "Candidate's Active Applications:\n{apps_str}\n\n"
        "Active Job Openings on the Platform:\n{jobs_str}\n\n"
        "INSTRUCTIONS:\n"
        "1. Be professional, encouraging, friendly, and helpful. Use markdown format.\n"
        "2. If the candidate asks about their application status, look it up in the 'Candidate's Active Applications' section above and answer directly.\n"
        "3. If they ask about job openings, suggest matching jobs from the 'Active Job Openings' list.\n"
        "4. If they ask about skill gaps, analyze the skills required for active job openings vs their current skills and recommend areas to improve.\n"
        "5. Keep responses concise, structured, and easy to read. Suggest actions the user can take."
    ).format(
        name=current_user.full_name,
        email=current_user.email,
        phone=cand.phone or "Not provided yet",
        skills=cand.skills or "None listed yet",
        experience=cand.experience or "None listed yet",
        education=cand.education or "None listed yet",
        apps_str=apps_str,
        jobs_str=jobs_str
    )

    # Compile messages
    messages = [{"role": "system", "content": system_prompt}]
    for msg in payload.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": payload.message})

    response_text = ""
    # Try calling NVIDIA API first
    if settings.NVIDIA_API_KEY:
        response_text = call_nvidia(messages)

    # Fallback to Gemini if NVIDIA key is not set or fails
    if not response_text and settings.GEMINI_API_KEY:
        # Format conversation history as a single string for Gemini
        gemini_prompt = ""
        for m in messages:
            role_name = "System" if m["role"] == "system" else ("User" if m["role"] == "user" else "Assistant")
            gemini_prompt += f"{role_name}: {m['content']}\n\n"
        gemini_prompt += "Assistant: "
        response_text = call_gemini(gemini_prompt)

    # Hardcoded fallback if both APIs fail or are unconfigured
    if not response_text:
        lower_msg = payload.message.lower()
        if "application" in lower_msg:
            response_text = (
                f"I checked your applications, {current_user.full_name}. Here is the status of your active application(s):\n\n"
                f"{apps_str}\n\n"
                "You can view more details on the jobs board!"
            )
        elif "job" in lower_msg or "openings" in lower_msg:
            response_text = (
                f"Here are the active job openings matching your interest:\n\n"
                f"{jobs_str[:400]}...\n\n"
                "Navigate to the Jobs section to view and apply."
            )
        else:
            response_text = (
                f"Hello {current_user.full_name}! I'm Baelyx, your AI Career Copilot. "
                f"Currently, our cloud AI connection is offline, but I can still tell you that you have {len(apps)} active application(s) "
                f"and your listed skills are: {cand.skills or 'none listed yet'}. How can I assist you with these?"
            )

    # Attach dynamic actions based on keywords in the reply
    actions = []
    response_lower = response_text.lower()
    if "resume builder" in response_lower or "resume score" in response_lower:
        actions.append({"label": "Open Resume Builder", "href": "/candidate/resume"})
    if "job" in response_lower or "jobs" in response_lower or "openings" in response_lower:
        actions.append({"label": "Browse Job Board", "href": "/candidate/jobs"})
    if "skill" in response_lower or "skill lab" in response_lower or "gap" in response_lower:
        actions.append({"label": "Open Skill Lab", "href": "/candidate/skill-lab"})
    if "application" in response_lower or "status" in response_lower:
        # Prevent duplicate buttons if Browse Jobs already added
        if not any(a["label"] == "Browse Job Board" for a in actions):
            actions.append({"label": "View Applications", "href": "/candidate/jobs"})

    return schemas.ChatCopilotResponse(response=response_text, actions=actions if actions else None)

# ─────────────── MCP UNIFIED CHAT & SESSIONS ───────────────

def generate_chat_title(first_message: str) -> str:
    try:
        prompt = (
            "You are a helpful assistant. Generate a short, concise, professional title "
            "(maximum 4 words) representing the user's first query in a chat session. "
            "Do not include quotes, markdown, punctuation, or explanations. Respond with ONLY the title.\n\n"
            f"Query: {first_message}\n\nTitle:"
        )
        title = call_gemini(prompt)
        if not title:
            title = call_nvidia(prompt)
        title = title.strip().replace('"', '').replace("'", "")
        if title and len(title.split()) <= 6:
            return title
    except Exception as e:
        logger.error(f"Error generating chat title: {e}")
    return first_message[:40] + "..." if len(first_message) > 40 else first_message


@router.post("/mcp/chat", response_model=schemas.MCPChatResponse)
async def mcp_chat(
    payload: schemas.MCPChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified MCP chat endpoint — routes through Supervisor Agent.
    Replaces mode-specific endpoints. All MCP widgets call this.
    """
    from app.agents.supervisor_agent import supervisor_agent
    from app.models.models import Candidate
    import uuid

    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    session_id = payload.session_id
    session = None

    if session_id:
        session = db.query(MCPChatSession).filter(
            MCPChatSession.id == session_id,
            MCPChatSession.user_id == current_user.id,
            MCPChatSession.is_deleted == False
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        # Create a new session
        title = generate_chat_title(payload.message)
        session = MCPChatSession(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            title=title,
            mode=payload.mode
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    # Load history from DB
    db_messages = db.query(MCPChatMessage).filter(
        MCPChatMessage.session_id == session_id
    ).order_by(MCPChatMessage.created_at.asc()).all()

    # Build history list of dicts for supervisor agent
    history = []
    for m in db_messages:
        history.append({
            "role": "user" if m.sender == "user" else "assistant",
            "content": m.text
        })

    # Save user's message
    user_msg = MCPChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        sender="user",
        text=payload.message
    )
    db.add(user_msg)
    db.commit()

    # Run supervisor agent
    result = supervisor_agent.route(
        message=payload.message,
        mode=payload.mode,
        candidate_id=cand.id,
        user_id=current_user.id,
        history=history,
        context_hint=payload.context_hint,
        db=db
    )

    # Convert action_cards (Pydantic objects) and actions to serializable dicts
    action_cards_data = []
    if result.action_cards:
        for card in result.action_cards:
            if hasattr(card, "dict"):
                action_cards_data.append(card.dict())
            elif hasattr(card, "model_dump"):
                action_cards_data.append(card.model_dump())
            else:
                action_cards_data.append(card)

    actions_data = []
    if hasattr(result, "actions") and result.actions:
        for action in result.actions:
            if hasattr(action, "dict"):
                actions_data.append(action.dict())
            elif hasattr(action, "model_dump"):
                actions_data.append(action.model_dump())
            else:
                actions_data.append(action)

    # Save assistant's message
    assistant_msg = MCPChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        sender="tush",
        text=result.response,
        actions=actions_data,
        action_cards=action_cards_data,
        memory_updated=result.memory_updated
    )
    db.add(assistant_msg)

    # Update session updated_at
    session.updated_at = datetime.utcnow()
    db.commit()

    # Broadcast user message and assistant message via WebSocket for instant updates
    try:
        await manager.broadcast_to_user(current_user.email, {
            "type": "mcp_chat_message",
            "session_id": session_id,
            "message": {
                "id": user_msg.id,
                "sender": "user",
                "text": user_msg.text,
                "created_at": user_msg.created_at.isoformat() if hasattr(user_msg.created_at, "isoformat") else str(user_msg.created_at)
            }
        })
        await manager.broadcast_to_user(current_user.email, {
            "type": "mcp_chat_message",
            "session_id": session_id,
            "message": {
                "id": assistant_msg.id,
                "sender": "tush",
                "text": assistant_msg.text,
                "actions": assistant_msg.actions,
                "action_cards": assistant_msg.action_cards,
                "memory_updated": assistant_msg.memory_updated,
                "created_at": assistant_msg.created_at.isoformat() if hasattr(assistant_msg.created_at, "isoformat") else str(assistant_msg.created_at)
            }
        })
    except Exception:
        pass

    return schemas.MCPChatResponse(
        response=result.response,
        action_cards=result.action_cards if result.action_cards else [],
        haq_required=result.haq_required,
        haq_item=result.haq_item,
        memory_updated=result.memory_updated,
        intent=result.intent,
        agent_used=result.agent_used,
        session_id=session_id
    )


@router.post("/mcp/chat/stream")
async def mcp_chat_stream(
    payload: schemas.MCPChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Unified MCP chat endpoint with Server-Sent Events (SSE) streaming.
    Streams assistant reply and action card metadata.
    """
    from app.agents.supervisor_agent import supervisor_agent
    from app.models.models import Candidate
    import uuid
    import asyncio

    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    session_id = payload.session_id
    session = None

    if session_id:
        session = db.query(MCPChatSession).filter(
            MCPChatSession.id == session_id,
            MCPChatSession.user_id == current_user.id,
            MCPChatSession.is_deleted == False
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")
    else:
        title = generate_chat_title(payload.message)
        session = MCPChatSession(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            title=title,
            mode=payload.mode
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        session_id = session.id

    db_messages = db.query(MCPChatMessage).filter(
        MCPChatMessage.session_id == session_id
    ).order_by(MCPChatMessage.created_at.asc()).all()

    history = []
    for m in db_messages:
        history.append({
            "role": "user" if m.sender == "user" else "assistant",
            "content": m.text
        })

    user_msg = MCPChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        sender="user",
        text=payload.message
    )
    db.add(user_msg)
    db.commit()

    async def sse_generator():
        try:
            # 1. Send session info instantly (prevents Vercel/Railway gateway timeout)
            session_payload = {
                "type": "session",
                "session_id": session_id,
                "title": session.title
            }
            yield f"data: {json.dumps(session_payload)}\n\n"
            await asyncio.sleep(0.01)

            # 2. Run supervisor agent (slow LLM call)
            # Run in executor to keep event loop unblocked
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: supervisor_agent.route(
                    message=payload.message,
                    mode=payload.mode,
                    candidate_id=cand.id,
                    user_id=current_user.id,
                    history=history,
                    context_hint=payload.context_hint,
                    db=db
                )
            )

            # Convert action_cards (Pydantic objects) and actions to serializable dicts
            action_cards_data = []
            if result.action_cards:
                for card in result.action_cards:
                    if hasattr(card, "dict"):
                        action_cards_data.append(card.dict())
                    elif hasattr(card, "model_dump"):
                        action_cards_data.append(card.model_dump())
                    else:
                        action_cards_data.append(card)

            actions_data = []
            if hasattr(result, "actions") and result.actions:
                for action in result.actions:
                    if hasattr(action, "dict"):
                        actions_data.append(action.dict())
                    elif hasattr(action, "model_dump"):
                        actions_data.append(action.model_dump())
                    else:
                        actions_data.append(action)

            # 3. Stream response text in chunks
            words = result.response.split(" ")
            for i, word in enumerate(words):
                chunk_text = word + (" " if i < len(words) - 1 else "")
                content_payload = {
                    "type": "content",
                    "text": chunk_text
                }
                yield f"data: {json.dumps(content_payload)}\n\n"
                await asyncio.sleep(0.015)  # smooth speed

            # 4. Save assistant reply to DB
            assistant_msg = MCPChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=current_user.id,
                sender="tush",
                text=result.response,
                actions=actions_data,
                action_cards=action_cards_data,
                memory_updated=result.memory_updated
            )
            db.add(assistant_msg)
            session.updated_at = datetime.utcnow()
            db.commit()

            # 5. Broadcast user message and assistant message via WebSocket for instant updates
            try:
                await manager.broadcast_to_user(current_user.email, {
                    "type": "mcp_chat_message",
                    "session_id": session_id,
                    "message": {
                        "id": user_msg.id,
                        "sender": "user",
                        "text": user_msg.text,
                        "created_at": user_msg.created_at.isoformat() if hasattr(user_msg.created_at, "isoformat") else str(user_msg.created_at)
                    }
                })
                await manager.broadcast_to_user(current_user.email, {
                    "type": "mcp_chat_message",
                    "session_id": session_id,
                    "message": {
                        "id": assistant_msg.id,
                        "sender": "tush",
                        "text": assistant_msg.text,
                        "actions": assistant_msg.actions,
                        "action_cards": assistant_msg.action_cards,
                        "memory_updated": assistant_msg.memory_updated,
                        "created_at": assistant_msg.created_at.isoformat() if hasattr(assistant_msg.created_at, "isoformat") else str(assistant_msg.created_at)
                    }
                })
            except Exception:
                pass

            # 6. Send done payload
            done_payload = {
                "type": "done",
                "action_cards": action_cards_data,
                "haq_required": result.haq_required,
                "haq_item": result.haq_item,
                "memory_updated": result.memory_updated,
                "intent": result.intent,
                "agent_used": result.agent_used
            }
            yield f"data: {json.dumps(done_payload)}\n\n"

        except Exception as e:
            logger.error(f"Error in sse_generator: {e}")
            yield f"data: {json.dumps({'type': 'error', 'text': f'Error: {str(e)}'})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.get("/mcp/sessions", response_model=schemas.MCPChatSessionListResponse)
def list_mcp_chat_sessions(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(MCPChatSession).filter(
        MCPChatSession.user_id == current_user.id,
        MCPChatSession.is_deleted == False,
        MCPChatSession.is_archived == False
    )

    if search:
        query = query.filter(MCPChatSession.title.ilike(f"%{search}%"))

    total_count = query.count()

    # Sort: Pinned first, then by updated_at desc
    sessions = query.order_by(
        MCPChatSession.is_pinned.desc(),
        MCPChatSession.updated_at.desc()
    ).offset((page - 1) * limit).limit(limit).all()

    import math
    pages = math.ceil(total_count / limit) if limit > 0 else 1

    return {
        "sessions": sessions,
        "total_count": total_count,
        "page": page,
        "pages": pages
    }


@router.get("/mcp/sessions/{session_id}/messages")
def get_mcp_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(MCPChatSession).filter(
        MCPChatSession.id == session_id,
        MCPChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = db.query(MCPChatMessage).filter(
        MCPChatMessage.session_id == session_id
    ).order_by(MCPChatMessage.created_at.asc()).all()

    return [{
        "id": m.id,
        "sender": m.sender,
        "text": m.text,
        "actions": m.actions,
        "action_cards": m.action_cards,
        "memory_updated": m.memory_updated,
        "created_at": m.created_at
    } for m in messages]


@router.put("/mcp/sessions/{session_id}", response_model=schemas.MCPChatSessionResponse)
def update_mcp_chat_session(
    session_id: str,
    payload: schemas.MCPChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(MCPChatSession).filter(
        MCPChatSession.id == session_id,
        MCPChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if payload.title is not None:
        session.title = payload.title
    if payload.is_pinned is not None:
        session.is_pinned = payload.is_pinned
    if payload.is_archived is not None:
        session.is_archived = payload.is_archived

    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


@router.delete("/mcp/sessions/{session_id}")
def delete_mcp_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(MCPChatSession).filter(
        MCPChatSession.id == session_id,
        MCPChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    session.is_deleted = True
    session.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Chat session deleted successfully"}


# ----------------- MESSAGES & LIVE CHAT -----------------

# ----------------- MESSAGES & LIVE CHAT -----------------

@router.get("/messages", response_model=List[schemas.MessageResponse])
def get_messages(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    # Build team chat ID if candidate is assigned to a hackathon team
    team_chat_id = None
    if cand.hackathon_team:
        import re
        team_name_clean = cand.hackathon_team.strip().lower()
        team_name_clean = re.sub(r'\s+', '_', team_name_clean)
        team_chat_id = f"team_{team_name_clean}"

    if team_chat_id:
        messages = db.query(Message).filter(
            (Message.candidate_id == cand.id) | (Message.chat_id == team_chat_id)
        ).order_by(Message.sent_at.asc()).all()
    else:
        messages = db.query(Message).filter(
            Message.candidate_id == cand.id
        ).order_by(Message.sent_at.asc()).all()
        
    return messages


@router.post("/messages", response_model=schemas.MessageResponse)
async def send_message(
    msg_in: schemas.MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    msg = Message(
        candidate_id=cand.id,
        chat_id=msg_in.chat_id,
        sender="user",
        sender_name=current_user.full_name or "User",
        text=msg_in.text,
        sent_at=datetime.utcnow(),
        read=False
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    msg_dict = {
        "id": msg.id,
        "candidate_id": msg.candidate_id,
        "chat_id": msg.chat_id,
        "sender": msg.sender,
        "sender_name": msg.sender_name,
        "text": msg.text,
        "sent_at": msg.sent_at.isoformat(),
        "read": msg.read
    }
    
    # Broadcast based on chat type (team group vs private chat)
    if msg_in.chat_id.startswith("team_") and cand.hackathon_team:
        # Broadcast to ALL members of the same hackathon team
        team_members = db.query(Candidate).filter(
            func.lower(Candidate.hackathon_team) == func.lower(cand.hackathon_team)
        ).all()
        for member in team_members:
            if member.user:
                await manager.broadcast_to_user(member.user.email, {
                    "type": "chat_message",
                    "chat_id": msg_in.chat_id,
                    "message": msg_dict
                })
    else:
        # Broadcast to candidate's own active sessions
        await manager.broadcast_to_user(current_user.email, {
            "type": "chat_message",
            "chat_id": msg_in.chat_id,
            "message": msg_dict
        })
        
    # Broadcast to admins so they can see live updates in the recruiter dashboard
    await manager.broadcast_to_admins({
        "type": "admin_chat_message",
        "candidate_id": cand.id,
        "chat_id": msg_in.chat_id,
        "message": msg_dict
    })
    
    return msg


@router.put("/candidates/{candidate_id}/hackathon", response_model=schemas.CandidateResponse)
def update_candidate_hackathon(
    candidate_id: int,
    assignment: schemas.CandidateHackathonUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if assignment.hackathon_team is not None:
        cand.hackathon_team = assignment.hackathon_team
    if assignment.assigned_mentor is not None:
        cand.assigned_mentor = assignment.assigned_mentor
    if assignment.hackathon_problem is not None:
        cand.hackathon_problem = assignment.hackathon_problem
    if assignment.hackathon_members is not None:
        cand.hackathon_members = assignment.hackathon_members
        
    db.commit()
    db.refresh(cand)
    return cand


@router.post("/admin/messages", response_model=schemas.MessageResponse)
async def admin_send_message(
    msg_in: schemas.AdminMessageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    cand = db.query(Candidate).filter(Candidate.id == msg_in.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
        
    msg = Message(
        candidate_id=cand.id,
        chat_id=msg_in.chat_id,
        sender=msg_in.sender, # support, recruiter, mentor
        sender_name=msg_in.sender_name,
        text=msg_in.text,
        sent_at=datetime.utcnow(),
        read=False
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    msg_dict = {
        "id": msg.id,
        "candidate_id": msg.candidate_id,
        "chat_id": msg.chat_id,
        "sender": msg.sender,
        "sender_name": msg.sender_name,
        "text": msg.text,
        "sent_at": msg.sent_at.isoformat(),
        "read": msg.read
    }
    
    # Broadcast to the candidate's websocket clients
    if cand.user:
        await manager.broadcast_to_user(cand.user.email, {
            "type": "chat_message",
            "chat_id": msg_in.chat_id,
            "message": msg_dict
        })
        
    # Broadcast back to admin sessions
    await manager.broadcast_to_admins({
        "type": "admin_chat_message",
        "candidate_id": cand.id,
        "chat_id": msg_in.chat_id,
        "message": msg_dict
    })
    
    return msg


@router.get("/admin/candidates/{candidate_id}/messages", response_model=List[schemas.MessageResponse])
def admin_get_messages(
    candidate_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    cand = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    team_chat_id = None
    if cand.hackathon_team:
        import re
        team_name_clean = cand.hackathon_team.strip().lower()
        team_name_clean = re.sub(r'\s+', '_', team_name_clean)
        team_chat_id = f"team_{team_name_clean}"

    if team_chat_id:
        messages = db.query(Message).filter(
            (Message.candidate_id == cand.id) | (Message.chat_id == team_chat_id)
        ).order_by(Message.sent_at.asc()).all()
    else:
        messages = db.query(Message).filter(
            Message.candidate_id == cand.id
        ).order_by(Message.sent_at.asc()).all()
        
    return messages


