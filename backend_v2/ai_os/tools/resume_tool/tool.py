import logging
from typing import Any, Dict

from .schemas import ParseResumeInput
from .validators import validate_parse_input
from .permissions import check_resume_permissions
from .handlers import handle_resume_parsing
from ..runtime.tool_context import ToolContext
from ...registry.tool_registry import tool_registry

logger = logging.getLogger("ai_os.tools.resume_tool.tool")

@tool_registry.register(
    name="upload_resume_pdf",
    description="Parses raw resume text and persists structural profile parameters (summary, skills, work history) to PostgreSQL.",
    input_schema=ParseResumeInput,
    permission="resume_parsing",
    retry_budget=3,
    timeout=20.0
)
async def upload_resume_pdf_tool(args: ParseResumeInput, context: ToolContext) -> Dict[str, Any]:
    """
    Unified Tool interface for resume parsing.
    Validates arguments, verifies permissions, and executes database persistence.
    """
    logger.info(f"Resume Tool: Executing upload_resume_pdf capability for candidate '{args.candidate_id}'")

    # 1. Run local parameter validation
    if not validate_parse_input(args):
        raise ValueError("Tool execution error: Invalid input parameters.")

    # 2. Run local ownership checks
    if not check_resume_permissions(args.candidate_id, context):
        raise PermissionError("Tool authorization failed: User lacks candidate profile access permissions.")

    # 3. Fetch database session from context memory manager
    db_session = None
    if context.memory and hasattr(context.memory, "checkpoint") and hasattr(context.memory.checkpoint, "db"):
        db_session = context.memory.checkpoint.db

    # 4. Invoke domain handler
    output = await handle_resume_parsing(args, db_session)
    
    return {
        "success": output.success,
        "profile_data": output.profile_data,
        "skills_count": output.extracted_skills_count
    }
