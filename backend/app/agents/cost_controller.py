"""
Cost Controller Agent — tracks and limits LLM token/character usage budgets.
"""
import logging
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import AIMentorUsage

logger = logging.getLogger("app.agents.cost_controller")

DAILY_CHAR_LIMIT = 500_000    # Daily character limit per user (~125k tokens)


class CostControllerAgent:
    
    def check_budget(self, user_id: int, db: Session) -> bool:
        """Returns True if OK to proceed, False if budget exceeded."""
        try:
            today_start = datetime.combine(date.today(), datetime.min.time())
            chars_sum = db.query(
                func.coalesce(func.sum(AIMentorUsage.prompt_chars + AIMentorUsage.completion_chars), 0)
            ).filter(
                AIMentorUsage.user_id == user_id,
                AIMentorUsage.created_at >= today_start
            ).scalar()
            
            if chars_sum > DAILY_CHAR_LIMIT:
                logger.warning(f"User {user_id} hit daily character limit: {chars_sum} chars used.")
                return False
            return True
        except Exception as e:
            logger.error(f"Error checking budget: {e}")
            return True  # Fail open
            
    def record(self, user_id: int, model_name: str, prompt_chars: int, completion_chars: int, db: Session):
        """Record the model call usage statistics."""
        try:
            import uuid
            usage = AIMentorUsage(
                id=str(uuid.uuid4()),
                user_id=user_id,
                model_name=model_name,
                prompt_chars=prompt_chars,
                completion_chars=completion_chars,
                created_at=datetime.utcnow()
            )
            db.add(usage)
            db.commit()
            logger.info(f"Recorded usage for user {user_id} on {model_name}: {prompt_chars} prompt, {completion_chars} completion chars.")
        except Exception as e:
            logger.error(f"Error recording usage: {e}")

    def select_model(self, prompt_text: str, user_id: int, db: Session) -> str:
        """Selects cheapest model (e.g. nvidia fallback) if daily usage is high."""
        try:
            prompt_chars = len(prompt_text)
            today_start = datetime.combine(date.today(), datetime.min.time())
            chars_sum = db.query(
                func.coalesce(func.sum(AIMentorUsage.prompt_chars + AIMentorUsage.completion_chars), 0)
            ).filter(
                AIMentorUsage.user_id == user_id,
                AIMentorUsage.created_at >= today_start
            ).scalar()
            
            if chars_sum > (DAILY_CHAR_LIMIT * 0.7) or prompt_chars > 10000:
                return "nvidia"
            return "gemini"
        except Exception:
            return "gemini"


cost_controller = CostControllerAgent()
