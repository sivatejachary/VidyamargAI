import logging
import re
from typing import Dict, Any, List

logger = logging.getLogger("ai_os.verification.verification")

class VerificationEngine:
    """
    Enforces security, checks response validation schemas, and scrubs PII.
    """
    def __init__(self):
        # Basic regex patterns for PII scrubbing
        self.email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+\.\w+")
        self.phone_pattern = re.compile(r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b")

    async def verify_output_schema(self, output: Dict[str, Any], required_keys: List[str]) -> bool:
        """
        Validates if tool output payload contains all required JSON schema fields.
        """
        logger.info(f"Verifying schema validation. Required keys: {required_keys}")
        
        missing_keys = [k for k in required_keys if k not in output]
        if missing_keys:
            logger.warning(f"Schema verification failed. Missing keys: {missing_keys}")
            return False
            
        logger.info("Schema verification completed successfully.")
        return True

    def scrub_pii(self, text: str) -> str:
        """
        Masks candidate email and phone details in logs to enforce privacy security.
        """
        logger.info("Scrubbing candidate PII records from execution data logs.")
        scrubbed = self.email_pattern.sub("[EMAIL_MASKED]", text)
        scrubbed = self.phone_pattern.sub("[PHONE_MASKED]", scrubbed)
        return scrubbed
