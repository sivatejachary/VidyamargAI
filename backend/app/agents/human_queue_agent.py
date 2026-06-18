"""
Human Queue Agent — manages all human-in-the-loop tasks (OTP, CAPTCHAs, consent).
Integrates Redis session persistence to allow seamless state rehydration (zero-restart execution).
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.mcp_models import HumanActionItem
from app.core.queue import redis_conn

logger = logging.getLogger("app.agents.human_queue")


class HumanQueueAgent:
    
    def create_task(
        self,
        user_id: int,
        agent_name: str,
        action_type: str,
        title: str,
        description: str,
        browser_state: Dict[str, Any],
        db: Session,
        expires_in_minutes: int = 15
    ) -> HumanActionItem:
        """Creates a persistent task requiring human attention, caching browser context in Redis."""
        # Create DB action item
        task = HumanActionItem(
            user_id=user_id,
            agent_name=agent_name,
            action_type=action_type,
            title=title,
            description=description,
            status="pending",
            payload={"action_type": action_type},
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Save exact browser context/state to Redis using task callback key
        if redis_conn and browser_state:
            try:
                state_key = f"redis:state:{task.callback_key}"
                redis_conn.setex(
                    state_key,
                    expires_in_minutes * 60,
                    json.dumps(browser_state)
                )
                logger.info(f"Saved browser state in Redis with key: {state_key}")
            except Exception as e:
                logger.error(f"Failed to cache browser state in Redis: {e}")
                
        # Send Notification (WebSocket / Email)
        try:
            from app.services.agent_activity_feed import log as feed_log
            feed_log(
                user_id=user_id,
                agent_name="Human Queue Agent",
                action="task_created",
                detail=f"Action Required: '{title}' task created in queue.",
                meta={"task_id": task.id, "action_type": action_type},
                db=db
            )
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            
        return task

    def get_browser_state(self, callback_key: str) -> Optional[Dict[str, Any]]:
        """Rehydrates cached browser state variables from Redis."""
        if not redis_conn:
            return None
        try:
            state_key = f"redis:state:{callback_key}"
            raw = redis_conn.get(state_key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to fetch browser state from Redis: {e}")
        return None

    def resolve_task(self, callback_key: str, resolution_data: Dict[str, Any], db: Session) -> bool:
        """Marks task resolved and cleans up cached Redis state context."""
        task = db.query(HumanActionItem).filter(HumanActionItem.callback_key == callback_key).first()
        if not task:
            logger.warning(f"Task with callback_key={callback_key} not found")
            return False
            
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        task.payload.update({"resolution": resolution_data})
        db.commit()
        
        # Remove Redis key
        if redis_conn:
            try:
                state_key = f"redis:state:{callback_key}"
                redis_conn.delete(state_key)
                logger.info(f"Purged resolved browser state key: {state_key}")
            except Exception as e:
                logger.error(f"Failed to clear Redis state: {e}")
                
        # Log to activity feed
        try:
            from app.services.agent_activity_feed import log as feed_log
            feed_log(
                user_id=task.user_id,
                agent_name="Human Queue Agent",
                action="task_resolved",
                detail=f"Resolved Action: '{task.title}' completed successfully.",
                meta={"task_id": task.id},
                db=db
            )
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            
        return True
