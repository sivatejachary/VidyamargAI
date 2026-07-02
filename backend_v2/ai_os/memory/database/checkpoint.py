import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import Column, String, DateTime, Text, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import declarative_base

logger = logging.getLogger("ai_os.memory.database.checkpoint")

Base = declarative_base()

class CheckpointModel(Base):
    """
    SQLAlchemy Model representing the serialized state of active/paused task loops.
    """
    __tablename__ = "agent_execution_checkpoints"

    id = Column(String(255), primary_key=True)
    session_id = Column(String(255), nullable=False, index=True)
    state_data = Column(JSONB, nullable=False) # Stores Blackboard variables, step history logs, and goal tree
    wait_event = Column(String(255), nullable=True) # Optional event we are waiting for (e.g. USER_APPROVAL)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CheckpointManager:
    """
    Handles serialization and persistence of agent execution states.
    """
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def save_checkpoint(
        self,
        checkpoint_id: str,
        session_id: str,
        state_data: Dict[str, Any],
        wait_event: Optional[str] = None
    ) -> bool:
        """
        Saves or updates an agent execution state checkpoint in PostgreSQL.
        """
        logger.info(f"Saving state checkpoint '{checkpoint_id}' for session '{session_id}' (Wait Event: '{wait_event}')")
        try:
            # Check if checkpoint already exists
            query = select(CheckpointModel).where(CheckpointModel.id == checkpoint_id)
            result = await self.db.execute(query)
            checkpoint = result.scalar_one_or_none()

            if checkpoint is None:
                checkpoint = CheckpointModel(
                    id=checkpoint_id,
                    session_id=session_id,
                    state_data=state_data,
                    wait_event=wait_event
                )
                self.db.add(checkpoint)
            else:
                checkpoint.state_data = state_data
                checkpoint.wait_event = wait_event
                checkpoint.updated_at = datetime.utcnow()

            await self.db.commit()
            logger.info(f"Checkpoint '{checkpoint_id}' saved successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to save state checkpoint: {e}")
            await self.db.rollback()
            return False

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads and returns a checkpoint state record from PostgreSQL.
        """
        logger.info(f"Loading state checkpoint: '{checkpoint_id}'")
        try:
            query = select(CheckpointModel).where(CheckpointModel.id == checkpoint_id)
            result = await self.db.execute(query)
            checkpoint = result.scalar_one_or_none()
            
            if checkpoint:
                return {
                    "id": checkpoint.id,
                    "session_id": checkpoint.session_id,
                    "state_data": checkpoint.state_data,
                    "wait_event": checkpoint.wait_event,
                    "created_at": checkpoint.created_at
                }
            logger.warning(f"No checkpoint state found for ID: '{checkpoint_id}'")
            return None
        except Exception as e:
            logger.error(f"Failed to load state checkpoint: {e}")
            return None

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Deletes a completed state checkpoint.
        """
        logger.info(f"Deleting state checkpoint: '{checkpoint_id}'")
        try:
            query = select(CheckpointModel).where(CheckpointModel.id == checkpoint_id)
            result = await self.db.execute(query)
            checkpoint = result.scalar_one_or_none()
            if checkpoint:
                await self.db.delete(checkpoint)
                await self.db.commit()
                logger.info(f"Checkpoint '{checkpoint_id}' deleted successfully.")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete state checkpoint: {e}")
            await self.db.rollback()
            return False
