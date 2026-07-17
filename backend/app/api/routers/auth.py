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
from app.core.security import (
    get_current_user,
    get_current_admin,
    generate_refresh_token,
    hash_token,
    create_access_token
)
from app.schemas import schemas
from app.models.models import *

from app.api.helpers import *
from app.core.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/auth/test-resend-directly")
def test_resend_directly():
    import os
    import urllib.request
    import json
    resend_api_key = os.getenv("RESEND_API_KEY", "")
    smtp_from = os.getenv("SMTP_FROM_EMAIL", "")
    
    if not resend_api_key:
        return {"error": "RESEND_API_KEY is not set in environment"}
        
    from_sender = smtp_from if (smtp_from and not smtp_from.endswith("@gmail.com")) else "onboarding@resend.dev"
    
    req_data = {
        "from": f"VidyamargAI <{from_sender}>",
        "to": ["anusha.chegg12@gmail.com"],
        "subject": "VidyamargAI - Resend Direct Test",
        "html": "<p>This is a direct diagnostics test from VidyamargAI.</p>"
    }
    
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            method="POST",
            data=json.dumps(req_data).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {resend_api_key}",
                "Content-Type": "application/json",
                "User-Agent": "VidyamargAI/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            body = json.loads(response.read().decode())
            return {
                "success": True,
                "status": status,
                "body": body,
                "from_sender": from_sender
            }
    except Exception as e:
        err_msg = str(e)
        if hasattr(e, "read"):
            err_msg += " | " + e.read().decode()
        return {
            "success": False,
            "error": err_msg,
            "from_sender": from_sender
        }


# ----------------- AUTHENTICATION -----------------

@router.post("/auth/signup", response_model=schemas.UserResponse)
@limiter.limit("5/minute")
def signup(request: Request, user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    role = (user_in.role or "candidate").strip().lower()
    if role not in ["candidate", "admin", "super_admin"]:
        role = "candidate"

    if role in ["admin", "super_admin"]:
        expected_key = os.getenv("ADMIN_REGISTRATION_KEY", "VM_ADMIN_2026")
        if user_in.security_key != expected_key:
            raise HTTPException(
                status_code=403,
                detail="Invalid Administrative Security Key. Access blocked."
            )

    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        email=user_in.email,
        password_hash=hashed_pwd,
        full_name=user_in.full_name,
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # If role is candidate, automatically create an empty candidate profile
    if user.role == "candidate":
        candidate = Candidate(user_id=user.id, status="Registered", current_step="Profile")
        db.add(candidate)
        db.commit()
        
    return user

@router.post("/auth/login", response_model=schemas.Token)
@limiter.limit("5/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.email, role=user.role)
    
    # Generate refresh token
    refresh_token = generate_refresh_token()
    token_hash = hash_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=7)
    db_refresh_token = UserRefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_refresh_token)
    db.commit()
    
    # Trigger event-driven login motivation agent update
    try:
        from app.agents.learning_os import trigger_learning_os_agents
        trigger_learning_os_agents(db, user.id, "new_login")
    except Exception as e:
        logger.error(f"Failed to trigger learning agents on login: {e}")
        
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name,
        "email": user.email,
        "refresh_token": refresh_token
    }

@router.post("/auth/refresh")
def refresh_token_endpoint(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    token_hash = hash_token(payload.refresh_token)
    db_token = db.query(UserRefreshToken).filter(
        UserRefreshToken.token_hash == token_hash
    ).first()
    
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    access_token = create_access_token(subject=user.email, role=user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/auth/logout")
def logout_endpoint(
    payload: schemas.RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    token_hash = hash_token(payload.refresh_token)
    db_token = db.query(UserRefreshToken).filter(
        UserRefreshToken.token_hash == token_hash
    ).first()
    
    if db_token:
        db.delete(db_token)
        db.commit()
        
    return {"message": "Successfully logged out"}


@router.get("/auth/me", response_model=schemas.UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user

# Rate limiting and OTP management helper functions
def delete_expired_otps(db: Session):
    try:
        from datetime import datetime
        db.query(OTP).filter(OTP.expiry_time < datetime.utcnow()).delete()
        db.commit()
    except Exception as e:
        logger.error(f"Error deleting expired OTPs: {e}")

def send_otp_html_email(email: str, code: str, db: Session):
    # Clean professional HTML email template matching user specification
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Reset Your Password - VidyamargAI</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f4f6f9; font-family: Arial, sans-serif;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f4f6f9; padding: 40px 20px;">
    <tr>
      <td align="center">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 520px; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color: #4f46e5; padding: 28px 32px; text-align: left;">
              <span style="color: #ffffff; font-size: 22px; font-weight: 700; letter-spacing: 0.3px;">VidyamargAI</span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding: 36px 32px 28px 32px; color: #374151; font-size: 15px; line-height: 1.7;">

              <p style="margin: 0 0 16px 0;">Hello,</p>

              <p style="margin: 0 0 24px 0;">
                We received a request to reset your VidyamargAI account password.
              </p>

              <p style="margin: 0 0 12px 0; font-weight: 600;">Your verification code is:</p>

              <!-- OTP Box -->
              <div style="text-align: center; margin: 24px 0;">
                <div style="display: inline-block; background-color: #f0f4ff; border: 2px solid #4f46e5; border-radius: 8px; padding: 14px 40px;">
                  <span style="font-size: 34px; font-weight: 700; letter-spacing: 8px; color: #4f46e5; font-family: 'Courier New', monospace;">{code}</span>
                </div>
              </div>

              <p style="margin: 0 0 24px 0; color: #6b7280; font-size: 14px; text-align: center;">
                This code will expire in <strong style="color: #374151;">10 minutes</strong>.
              </p>

              <p style="margin: 0 0 24px 0;">
                If you did not request a password reset, please ignore this email.
              </p>

              <p style="margin: 0;">
                Regards,<br>
                <strong>VidyamargAI Team</strong>
              </p>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color: #f9fafb; padding: 18px 32px; border-top: 1px solid #e5e7eb;">
              <p style="margin: 0; font-size: 12px; color: #9ca3af; text-align: center;">
                This is an automated message. Please do not reply to this email.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    import os
    import smtplib
    import urllib.request
    import json
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        smtp_port = 587
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    smtp_from = os.getenv("SMTP_FROM_EMAIL", "noreply@vidyamargai.com")

    subject = "Password Reset Verification Code - VidyamargAI"

    # Method 1: Try Resend HTTPS API (Port 443)
    resend_api_key = os.getenv("RESEND_API_KEY", "")
    if resend_api_key:
        try:
            # Resend requires a verified domain sender or onboarding@resend.dev
            from_sender = smtp_from if (smtp_from and not smtp_from.endswith("@gmail.com")) else "onboarding@resend.dev"
            req_data = {
                "from": f"VidyamargAI <{from_sender}>",
                "to": [email],
                "subject": subject,
                "html": html_content
            }
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                method="POST",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "VidyamargAI/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode())
                logger.info(f"OTP sent successfully via Resend API to {email}: {res_body}")
                return
        except Exception as e:
            logger.error(f"Resend API sending failed, trying fallback: {e}")

    # Method 2: Try SendGrid HTTPS API (Port 443)
    sendgrid_api_key = os.getenv("SENDGRID_API_KEY", "")
    if sendgrid_api_key:
        try:
            from_sender = smtp_from if smtp_from else "noreply@vidyamargai.com"
            req_data = {
                "personalizations": [{"to": [{"email": email}]}],
                "from": {"email": from_sender, "name": "VidyamargAI"},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}]
            }
            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                method="POST",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {sendgrid_api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "VidyamargAI/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                logger.info(f"OTP sent successfully via SendGrid API to {email}")
                return
        except Exception as e:
            logger.error(f"SendGrid API sending failed, trying fallback: {e}")

    # Method 3: Try Brevo HTTPS API (Port 443)
    brevo_api_key = os.getenv("BREVO_API_KEY", "")
    if brevo_api_key:
        try:
            from_sender = smtp_from if smtp_from else "noreply@vidyamargai.com"
            req_data = {
                "sender": {"name": "VidyamargAI", "email": from_sender},
                "to": [{"email": email}],
                "subject": subject,
                "htmlContent": html_content
            }
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                method="POST",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "VidyamargAI/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = json.loads(response.read().decode())
                logger.info(f"OTP sent successfully via Brevo API to {email}: {res_body}")
                return
        except Exception as e:
            logger.error(f"Brevo API sending failed, trying fallback: {e}")

    # Method 4: Fallback to standard SMTP (Port 587)
    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = email
            
            # Attach plain and HTML body
            plain_body = f"Your VidyamargAI verification code is: {code}\nThis code is valid for 10 minutes."
            msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_from, [email], msg.as_string())
            server.quit()
            logger.info(f"Password reset OTP sent via SMTP to {email}")
        except Exception as e:
            logger.error(f"SMTP failed to send OTP: {e}")
    else:
        logger.warning(f"No email API keys or SMTP credentials configured. Printed OTP for {email}: {code}")

    # Create EmailNotification record so candidates can check their notifications in-app (for testing/logs copy)
    try:
        user = db.query(User).filter(User.email == email).first()
        if user and user.role == "candidate":
            candidate = user.candidate
            if candidate:
                email_notif = EmailNotification(
                    candidate_id=candidate.id,
                    sender=smtp_from,
                    recipient=email,
                    subject=subject,
                    body=f"Your VidyamargAI verification code is: {code}\nThis code is valid for 10 minutes.",
                    read=False
                )
                db.add(email_notif)
                db.commit()
    except Exception as e:
        logger.error(f"Failed to create EmailNotification log: {e}")

@router.post("/auth/forgot-password")
def forgot_password(req: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    # 1. Delete expired OTPs automatically
    delete_expired_otps(db)

    # 2. Check if email is registered
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")
    
    # 3. Rate limiting check (max 3 OTP requests per 15 minutes per email)
    from datetime import datetime, timedelta
    fifteen_minutes_ago = datetime.utcnow() - timedelta(minutes=15)
    recent_otps = db.query(OTP).filter(
        OTP.email == req.email,
        OTP.created_at >= fifteen_minutes_ago
    ).count()
    
    if recent_otps >= 3:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Max 3 requests per 15 minutes. Please try again later."
        )
        
    # 4. Generate random 6-digit OTP
    import random
    code = f"{random.randint(100000, 999999)}"
    expiry = datetime.utcnow() + timedelta(minutes=10)
    
    # 5. Save OTP to DB (email, otp, expiry_time, used=False)
    otp_entry = OTP(
        email=req.email,
        otp=code,
        expiry_time=expiry,
        used=False
    )
    db.add(otp_entry)
    db.commit()
    
    # 6. Send OTP using SMTP
    send_otp_html_email(req.email, code, db)
    
    # 7. Success response (NEVER return OTP in response body or UI)
    return {"message": "A verification code has been sent to your registered email address."}

@router.post("/auth/reset-password")
def reset_password(req: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    # 1. Check if email is registered
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email not registered")
        
    # 2. Check if there is a valid, unused, unexpired OTP for this email
    from datetime import datetime
    otp_record = db.query(OTP).filter(
        OTP.email == req.email,
        OTP.otp == req.code,
        OTP.used == False,
        OTP.expiry_time > datetime.utcnow()
    ).first()
    
    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")
        
    # 3. Hash password using bcrypt before saving
    hashed_pwd = get_password_hash(req.new_password)
    user.password_hash = hashed_pwd
    
    # 4. Mark OTP as used
    otp_record.used = True
    
    db.commit()
    
    # 5. Clean up expired OTPs
    delete_expired_otps(db)
    
    return {"message": "Password updated successfully"}


@router.get("/users/me/preferences", response_model=schemas.UserPreferenceSchema)
def get_user_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.models import UserPreference
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id, theme="light")
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.put("/users/me/preferences", response_model=schemas.UserPreferenceSchema)
def update_user_preferences(
    req: schemas.UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.models.models import UserPreference
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not prefs:
        prefs = UserPreference(user_id=current_user.id, theme=req.theme)
        db.add(prefs)
    else:
        prefs.theme = req.theme
    
    db.commit()
    db.refresh(prefs)

    # 1. Update Redis Cache & publish to Pub/Sub sync channel
    from app.services.job_cache import get_redis_client
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            redis_client.set(f"user:preferences:{current_user.id}", json.dumps({"theme": req.theme}))
            
            sync_payload = {
                "room": f"user:{current_user.id}",
                "event": "theme:sync",
                "payload": {"theme": req.theme},
                "senderId": current_user.id
            }
            redis_client.publish("cache_events:sync", json.dumps(sync_payload))
        except Exception as e:
            logger.error(f"Error publishing theme sync event: {e}")

    return prefs






# ----------------- JOBS -----------------

import re
from typing import Tuple

