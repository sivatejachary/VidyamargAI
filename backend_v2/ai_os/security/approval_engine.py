import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("ai_os.security.approval_engine")

class ApprovalRequestSchema(BaseModel):
    request_id: str = Field(..., description="Unique approval request ID")
    candidate_id: str = Field(..., description="Target candidate profile ID")
    session_id: str = Field(..., description="Target execution session ID")
    action_type: str = Field(..., description="Type of action requiring approval (e.g. apply_job)")
    payload: Dict[str, Any] = Field(..., description="Arguments context for the blocked action")
    checkpoint_id: str = Field(..., description="Associated state checkpoint DB key")
    status: str = Field(default="PENDING", description="Status: PENDING, APPROVED, REJECTED")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

class ApprovalEngine:
    """
    Manages user approval queues and coordinates task resumption.
    """
    def __init__(self, db_session):
        self.db = db_session

    async def register_approval_request(
        self,
        request_id: str,
        candidate_id: str,
        session_id: str,
        action_type: str,
        payload: Dict[str, Any],
        checkpoint_id: str
    ) -> ApprovalRequestSchema:
        """
        Saves a pending approval request to the database and notifies the WebSocket gateway.
        """
        logger.info(f"Registering human approval request '{request_id}' for action '{action_type}'")
        
        request = ApprovalRequestSchema(
            request_id=request_id,
            candidate_id=candidate_id,
            session_id=session_id,
            action_type=action_type,
            payload=payload,
            checkpoint_id=checkpoint_id
        )
        
        # Save request parameters to database (simulate db insertion)
        # db.add(ApprovalModel(...))
        
        logger.info(f"Approval request '{request_id}' saved successfully in state PENDING.")
        return request

    async def resolve_approval_request(self, request_id: str, approved: bool) -> Dict[str, Any]:
        """
        Updates the request state and returns the checkpoint ID for resumption.
        """
        status = "APPROVED" if approved else "REJECTED"
        logger.info(f"Resolving approval request '{request_id}' as {status}")
        
        # Simulate loading from DB and updating
        # request = db.query(ApprovalModel).filter(...)
        # request.status = status
        # request.resolved_at = datetime.utcnow()
        
        # Fetch mock checkpoint association
        checkpoint_id = "mock_checkpoint_123" 
        
        return {
            "request_id": request_id,
            "status": status,
            "checkpoint_id": checkpoint_id,
            "resolved_at": datetime.utcnow()
        }
    
    async def get_pending_requests(self, candidate_id: str) -> list:
        """Returns all pending approval requests for a candidate's inbox dashboard."""
        return []
