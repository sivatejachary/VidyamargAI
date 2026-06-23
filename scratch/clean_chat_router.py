import os
import re

file_path = r"c:\Users\jshiv\Downloads\shivateja\backend\app\api\routers\chat.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add StreamingResponse import at the top
if "StreamingResponse" not in content:
    content = "from fastapi.responses import StreamingResponse\n" + content

# Replace chat_copilot function
# We locate from @router.post("/chat/copilot" to def generate_chat_title
copilot_pattern = re.compile(
    r'@router\.post\("/chat/copilot".*?def generate_chat_title\(', 
    re.DOTALL
)

new_copilot = """@router.post("/chat/copilot", response_model=schemas.ChatCopilotResponse)
async def chat_copilot(
    payload: schemas.ChatCopilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch candidate details
    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    lower_message = payload.message.lower()
    
    # Intercept job/apply queries
    if any(k in lower_message for k in ["apply", "job", "opening", "recruiter", "interview", "assessment"]):
        response_text = (
            "Job application and recruitment features have been deactivated on VidyaMarg AI. "
            "I can assist you with your learning progress, courses, resume optimization, and skill development."
        )
        return schemas.ChatCopilotResponse(
            response=response_text,
            actions=[{"label": "Open Skill Lab", "href": "/candidate/skill-lab"}]
        )

    # General career copilot system prompt (job-free)
    system_prompt = (
        "You are Baelyx, an autonomous AI Career Copilot on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.\\n\\n"
        "Here is the candidate's profile data:\\n"
        f"- Name: {current_user.full_name}\\n"
        f"- Email: {current_user.email}\\n"
        f"- Phone: {cand.phone or 'Not provided'}\\n"
        f"- Skills: {cand.skills or 'None listed yet'}\\n"
        f"- Experience: {cand.experience or 'None listed yet'}\\n"
        f"- Education: {cand.education or 'None listed yet'}\\n\\n"
        "INSTRUCTIONS:\\n"
        "1. Be professional, encouraging, friendly, and helpful. Use markdown format.\\n"
        "2. Help the candidate build their learning roadmap, recommend courses, or optimize their skills.\\n"
        "3. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
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

    # Fallback to Gemini
    if not response_text and settings.GEMINI_API_KEY:
        gemini_prompt = ""
        for m in messages:
            role_name = "System" if m["role"] == "system" else ("User" if m["role"] == "user" else "Assistant")
            gemini_prompt += f"{role_name}: {m['content']}\\n\\n"
        gemini_prompt += "Assistant: "
        response_text = call_gemini(gemini_prompt)

    if not response_text:
        response_text = (
            f"Hello {current_user.full_name}! I'm Baelyx, your AI Career Copilot. "
            f"Our cloud AI connection is temporarily offline. How can I assist you with your learning goals today?"
        )

    actions = []
    response_lower = response_text.lower()
    if "resume" in response_lower:
        actions.append({"label": "Open Resume Builder", "href": "/candidate/resume"})
    if "course" in response_lower or "skill" in response_lower:
        actions.append({"label": "Open Skill Lab", "href": "/candidate/skill-lab"})

    return schemas.ChatCopilotResponse(response=response_text, actions=actions if actions else None)


def generate_chat_title("""

content, count1 = copilot_pattern.subn(new_copilot, content)
print(f"Substituted chat_copilot: {count1} occurrence(s)")

# Replace mcp_chat and mcp_chat_stream functions
# We locate from @router.post("/mcp/chat" to @router.get("/mcp/sessions"
mcp_pattern = re.compile(
    r'@router\.post\("/mcp/chat".*?@router\.get\("/mcp/sessions"', 
    re.DOTALL
)

new_mcp = """@router.post("/mcp/chat", response_model=schemas.MCPChatResponse)
async def mcp_chat(
    payload: schemas.MCPChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.models import Candidate
    import uuid

    cand = db.query(Candidate).filter(Candidate.user_id == current_user.id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    session_id = payload.session_id
    if not session_id:
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

    # Load history
    db_messages = db.query(MCPChatMessage).filter(
        MCPChatMessage.session_id == session_id
    ).order_by(MCPChatMessage.created_at.asc()).all()

    messages = [{
        "role": "system", 
        "content": (
            "You are Tush, an autonomous AI Career Assistant on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.\\n\\n"
            "INSTRUCTIONS:\\n"
            "1. Be professional, encouraging, friendly, and helpful. Use markdown format.\\n"
            "2. Help the candidate with courses, learning paths, and skill lab. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
        )
    }]
    for m in db_messages[:-1]:
        messages.append({
            "role": "user" if m.sender == "user" else "assistant",
            "content": m.text
        })
    messages.append({"role": "user", "content": payload.message})

    response_text = ""
    if settings.NVIDIA_API_KEY:
        response_text = call_nvidia(messages)
    if not response_text and settings.GEMINI_API_KEY:
        gemini_prompt = ""
        for m in messages:
            role_name = "System" if m["role"] == "system" else ("User" if m["role"] == "user" else "Assistant")
            gemini_prompt += f"{role_name}: {m['content']}\\n\\n"
        gemini_prompt += "Assistant: "
        response_text = call_gemini(gemini_prompt)

    if not response_text:
        response_text = "I am currently offline. How can I assist you with your learning goals?"

    # Save assistant reply
    assistant_msg = MCPChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        sender="tush",
        text=response_text,
        actions=[],
        action_cards=[],
        memory_updated=False
    )
    db.add(assistant_msg)
    db.commit()

    return schemas.MCPChatResponse(
        response=response_text,
        action_cards=[],
        haq_required=False,
        haq_item=None,
        memory_updated=False,
        intent="general",
        agent_used="assistant",
        session_id=session_id
    )


@router.post("/mcp/chat/stream")
async def mcp_chat_stream(
    payload: schemas.MCPChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    user_msg = MCPChatMessage(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=current_user.id,
        sender="user",
        text=payload.message
    )
    db.add(user_msg)
    db.commit()

    # Load history
    db_messages = db.query(MCPChatMessage).filter(
        MCPChatMessage.session_id == session_id
    ).order_by(MCPChatMessage.created_at.asc()).all()

    messages = [{
        "role": "system", 
        "content": (
            "You are Tush, an autonomous AI Career Assistant on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.\\n\\n"
            "INSTRUCTIONS:\\n"
            "1. Be professional, encouraging, friendly, and helpful. Use markdown format.\\n"
            "2. Help the candidate with courses, learning paths, and skill lab. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
        )
    }]
    for m in db_messages[:-1]:
        messages.append({
            "role": "user" if m.sender == "user" else "assistant",
            "content": m.text
        })
    messages.append({"role": "user", "content": payload.message})

    async def sse_generator():
        try:
            session_payload = {
                "type": "session",
                "session_id": session_id,
                "title": session.title
            }
            yield f"data: {json.dumps(session_payload)}\\n\\n"
            await asyncio.sleep(0.01)

            response_text = ""
            if settings.NVIDIA_API_KEY:
                response_text = call_nvidia(messages)
            if not response_text and settings.GEMINI_API_KEY:
                gemini_prompt = ""
                for m in messages:
                    role_name = "System" if m["role"] == "system" else ("User" if m["role"] == "user" else "Assistant")
                    gemini_prompt += f"{role_name}: {m['content']}\\n\\n"
                gemini_prompt += "Assistant: "
                response_text = call_gemini(gemini_prompt)

            if not response_text:
                response_text = "I am currently offline. How can I assist you with your learning goals?"

            # Stream the response
            words = response_text.split(" ")
            for i, word in enumerate(words):
                chunk_text = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps({'type': 'content', 'text': chunk_text})}\\n\\n"
                await asyncio.sleep(0.015)

            assistant_msg = MCPChatMessage(
                id=str(uuid.uuid4()),
                session_id=session_id,
                user_id=current_user.id,
                sender="tush",
                text=response_text,
                actions=[],
                action_cards=[],
                memory_updated=False
            )
            db.add(assistant_msg)
            session.updated_at = datetime.utcnow()
            db.commit()

            yield f"data: {json.dumps({'type': 'done', 'action_cards': [], 'haq_required': False, 'haq_item': None, 'memory_updated': False, 'intent': 'general', 'agent_used': 'assistant'})}\\n\\n"
        except Exception as e:
            logger.error(f"Error in sse_generator: {e}")
            yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\\n\\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@router.get("/mcp/sessions" """

content, count2 = mcp_pattern.subn(new_mcp, content)
print(f"Substituted mcp_chat: {count2} occurrence(s)")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
