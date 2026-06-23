file_path = r"c:\Users\jshiv\Downloads\shivateja\backend\app\api\routers\chat.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's replace the broken string for Baelyx
broken_baelyx = '''    system_prompt = (
        "You are Baelyx, an autonomous AI Career Copilot on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.

"
        "Here is the candidate's profile data:
"
        f"- Name: {current_user.full_name}
"
        f"- Email: {current_user.email}
"
        f"- Phone: {cand.phone or 'Not provided'}
"
        f"- Skills: {cand.skills or 'None listed yet'}
"
        f"- Experience: {cand.experience or 'None listed yet'}
"
        f"- Education: {cand.education or 'None listed yet'}

"
        "INSTRUCTIONS:
"
        "1. Be professional, encouraging, friendly, and helpful. Use markdown format.
"
        "2. Help the candidate build their learning roadmap, recommend courses, or optimize their skills.
"
        "3. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
    )'''

fixed_baelyx = '''    system_prompt = (
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
    )'''

# Normalize line endings to LF first for search, then restore CRLF if needed
content_lf = content.replace("\r\n", "\n")
broken_baelyx_lf = broken_baelyx.replace("\r\n", "\n")
fixed_baelyx_lf = fixed_baelyx.replace("\r\n", "\n")

content_lf = content_lf.replace(broken_baelyx_lf, fixed_baelyx_lf)

# Now do the same for the first Tush system prompt
broken_tush1 = '''    messages = [{
        "role": "system", 
        "content": (
            "You are Tush, an autonomous AI Career Assistant on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.

"
            "INSTRUCTIONS:
"
            "1. Be professional, encouraging, friendly, and helpful. Use markdown format.
"
            "2. Help the candidate with courses, learning paths, and skill lab. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
        )
    }]'''

fixed_tush1 = '''    messages = [{
        "role": "system", 
        "content": (
            "You are Tush, an autonomous AI Career Assistant on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.\\n\\n"
            "INSTRUCTIONS:\\n"
            "1. Be professional, encouraging, friendly, and helpful. Use markdown format.\\n"
            "2. Help the candidate with courses, learning paths, and skill lab. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
        )
    }]'''

broken_tush1_lf = broken_tush1.replace("\r\n", "\n")
fixed_tush1_lf = fixed_tush1.replace("\r\n", "\n")

content_lf = content_lf.replace(broken_tush1_lf, fixed_tush1_lf)

# Do the same for the second Tush system prompt and sse response
broken_tush2 = '''    messages = [{
        "role": "system", 
        "content": (
            "You are Tush, an autonomous AI Career Assistant on the VidyaMarg AI platform. Your goal is to guide the candidate in their learning and skill development journey.

"
            "INSTRUCTIONS:
"
            "1. Be professional, encouraging, friendly, and helpful. Use markdown format.
"
            "2. Help the candidate with courses, learning paths, and skill lab. Do NOT mention job vacancies, recruitment, screening, interviews, or hiring companies."
        )
    }]'''

# The second broken block contains more multi-line parts:
# yield f"data: {json.dumps(session_payload)}\n\n" got broken as:
# yield f"data: {json.dumps(session_payload)}\n\n"
# Let's inspect other yields in content_lf
content_lf = content_lf.replace('yield f"data: {json.dumps(session_payload)}\n\n"', 'yield f"data: {json.dumps(session_payload)}\\n\\n"')
content_lf = content_lf.replace('f"{role_name}: {m[\'content\']}\n\n"', 'f"{role_name}: {m[\'content\']}\\n\\n"')
content_lf = content_lf.replace("yield f\"data: {json.dumps({'type': 'content', 'text': chunk_text})}\n\n\"", "yield f\"data: {json.dumps({'type': 'content', 'text': chunk_text})}\\n\\n\"")
content_lf = content_lf.replace("yield f\"data: {json.dumps({'type': 'done', 'action_cards': [], 'haq_required': False, 'haq_item': None, 'memory_updated': False, 'intent': 'general', 'agent_used': 'assistant'})}\n\n\"", "yield f\"data: {json.dumps({'type': 'done', 'action_cards': [], 'haq_required': False, 'haq_item': None, 'memory_updated': False, 'intent': 'general', 'agent_used': 'assistant'})}\\n\\n\"")
content_lf = content_lf.replace("yield f\"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n\"", "yield f\"data: {json.dumps({'type': 'error', 'text': str(e)})}\\n\\n\"")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content_lf.replace("\n", "\r\n"))

print("Replacements complete.")
