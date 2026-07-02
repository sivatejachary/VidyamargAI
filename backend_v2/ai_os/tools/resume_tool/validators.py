import logging
from .schemas import ParseResumeInput

logger = logging.getLogger("ai_os.tools.resume_tool.validators")

def validate_parse_input(args: ParseResumeInput) -> bool:
    """
    Validates that the input payload is structured and non-empty.
    """
    if not args.candidate_id or args.candidate_id.strip() == "":
        logger.error("Validation error: Candidate ID is blank.")
        return False
        
    if not args.raw_text or args.raw_text.strip() == "":
        logger.error("Validation error: Raw resume text is empty.")
        return False
        
    # Enforce minimum size threshold (e.g. 50 characters)
    if len(args.raw_text) < 50:
        logger.error("Validation error: Raw text payload is too small to represent a valid resume.")
        return False

    return True
