from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import re

class GoalManager:
    """
    Goal Manager evaluates query properties, determines if a task is recurring (monitoring),
    and checks if actions require explicit user/human confirmation.
    """
    
    @staticmethod
    def classify_goal(query: str) -> Dict[str, Any]:
        """
        Classifies user query to detect if it requires:
        - recurring background monitoring
        - human-in-the-loop approval
        """
        # Determine if recurring monitoring is requested
        is_recurring = False
        schedule = None
        
        lower_query = query.lower()
        if "monitor" in lower_query or "alert" in lower_query or "every day" in lower_query or "daily" in lower_query:
            is_recurring = True
            # Default to daily at 9 AM
            schedule = "0 9 * * *"
            if "weekly" in lower_query or "every week" in lower_query:
                schedule = "0 9 * * 1"  # Weekly on Mondays at 9 AM
                
        # Determine if human approval is needed
        requires_approval = False
        approval_reason = None
        
        if any(keyword in lower_query for keyword in ["apply", "submit", "outreach", "message recruiter", "pay", "delete"]):
            requires_approval = True
            approval_reason = "Action involves external communications, application submissions, or data mutations."
            
        return {
            "is_recurring": is_recurring,
            "schedule": schedule,
            "requires_approval": requires_approval,
            "approval_reason": approval_reason
        }

    @staticmethod
    def schedule_monitoring_task(
        db: Session, 
        user_id: int, 
        name: str, 
        query: str, 
        schedule: str
    ) -> Any:
        """
        Saves a BackgroundMonitoringTask to the database.
        """
        from app.models.mcp_models import BackgroundMonitoringTask
        
        # Calculate next run time (default to 24 hours from now for simple daily schedule)
        next_run = datetime.utcnow() + timedelta(days=1)
        if "1" in schedule: # Weekly
            next_run = datetime.utcnow() + timedelta(days=7)
            
        task = BackgroundMonitoringTask(
            user_id=user_id,
            name=name,
            query=query,
            schedule=schedule,
            next_run_at=next_run,
            is_active=True
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task
