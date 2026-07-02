import asyncio
import logging
import time
from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models.mcp_models import BackgroundMonitoringTask, AgentExecutionHistory
from app.agents.supervisor_agent import supervisor_agent
from app.models.models import User

logger = logging.getLogger("app.workers.task_worker")

async def run_pending_background_tasks(db):
    """
    Finds active, pending background monitoring tasks and runs the autonomous agent for them.
    """
    now = datetime.utcnow()
    tasks = db.query(BackgroundMonitoringTask).filter(
        BackgroundMonitoringTask.is_active == True,
        BackgroundMonitoringTask.next_run_at <= now
    ).all()
    
    if not tasks:
        return
        
    for task in tasks:
        logger.info(f"Running background monitoring task '{task.name}' for user ID {task.user_id}")
        user = db.query(User).filter(User.id == task.user_id).first()
        if not user:
            logger.warning(f"User not found for task ID {task.id}. Disabling task.")
            task.is_active = False
            db.commit()
            continue
            
        session_id = f"bg_session_{task.id}_{int(time.time())}"
        try:
            result = await supervisor_agent.route(
                db=db,
                user_id=user.id,
                user_role=user.role,
                session_id=session_id,
                query=task.query
            )
            
            task.last_run_at = now
            
            # Calculate next scheduling run time based on schedule string
            interval = timedelta(days=1)
            sched_lower = task.schedule.lower()
            if "week" in sched_lower:
                interval = timedelta(weeks=1)
            elif "hour" in sched_lower:
                interval = timedelta(hours=1)
            elif "minute" in sched_lower:
                interval = timedelta(minutes=5)
                
            task.next_run_at = now + interval
            logger.info(f"Completed task '{task.name}'. Status: {result.get('status')}. Next run scheduled at: {task.next_run_at}")
        except Exception as e:
            logger.error(f"Failed to execute background task {task.name}: {e}")
            task.next_run_at = now + timedelta(minutes=30)
            
        db.commit()

async def background_monitoring_worker():
    """
    Infinite worker loop that polls database for pending tasks every 10 seconds.
    """
    logger.info("Background task monitoring worker started successfully.")
    while True:
        try:
            db = SessionLocal()
            try:
                await run_pending_background_tasks(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in background monitoring worker loop: {e}")
            
        await asyncio.sleep(10)
