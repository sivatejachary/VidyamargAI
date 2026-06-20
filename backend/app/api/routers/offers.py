from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Response, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timedelta
import json
import logging
import os
import uuid
import time
import asyncio

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, get_current_admin
from app.schemas import schemas
from app.models.models import *

from app.api.helpers import *
from app.api.helpers import _check_resume_upload_rate_limit, _LIVE_JOB_STORE, _RESUME_UPLOAD_TIMESTAMPS

logger = logging.getLogger(__name__)

router = APIRouter()

# ----------------- OFFERS & ONBOARDING -----------------

@router.get("/offers/{app_id}", response_model=schemas.OfferResponse)
def get_offer_letter(app_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    offer = db.query(Offer).filter(Offer.application_id == app_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not generated")
    return offer

@router.post("/offers/{offer_id}/respond")
async def respond_to_offer(offer_id: int, accept: bool, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    offer.status = "accepted" if accept else "rejected"
    offer.responded_at = datetime.utcnow()
    db.commit()
    
    app_id = offer.application_id
    if accept:
        # Trigger onboarding agent
        await orchestrator.run_onboarding_agent(db, app_id)
        
    return {"message": "Offer status updated", "status": offer.status}


