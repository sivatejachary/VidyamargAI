from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    email: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = "candidate"  # candidate, admin

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserPreferenceSchema(BaseModel):
    theme: str

    class Config:
        from_attributes = True

class UserPreferenceUpdate(BaseModel):
    theme: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    created_at: Optional[datetime] = None
    preferences: Optional[UserPreferenceSchema] = None

    class Config:
        from_attributes = True

class CandidateProfileUpdate(BaseModel):
    phone: Optional[str] = None
    address: Optional[str] = None
    education: Optional[str] = None  # JSON encoded
    experience: Optional[str] = None # JSON encoded
    skills: Optional[str] = None     # Comma separated
    projects: Optional[str] = None   # JSON encoded
    certifications: Optional[str] = None # Comma separated
    summary: Optional[str] = None
    achievements: Optional[str] = None
    languages: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    parsed_name: Optional[str] = None
    parsed_email: Optional[str] = None

class CandidateResponse(BaseModel):
    id: int
    user_id: int
    phone: Optional[str]
    address: Optional[str]
    education: Optional[str]
    experience: Optional[str]
    skills: Optional[str]
    projects: Optional[str]
    certifications: Optional[str]
    summary: Optional[str] = None
    achievements: Optional[str] = None
    languages: Optional[str] = None
    linkedin: Optional[str]
    github: Optional[str]
    portfolio: Optional[str]
    status: str
    current_step: str
    hackathon_team: Optional[str] = None
    assigned_mentor: Optional[str] = None
    hackathon_problem: Optional[str] = None
    hackathon_members: Optional[str] = None
    parsed_name: Optional[str] = None
    parsed_email: Optional[str] = None
    user: UserResponse

    class Config:
        from_attributes = True

class CandidateHackathonUpdate(BaseModel):
    hackathon_team: Optional[str] = None
    assigned_mentor: Optional[str] = None
    hackathon_problem: Optional[str] = None
    hackathon_members: Optional[str] = None

class ATSAnalysisRequest(BaseModel):
    job_id: Optional[int] = None
    job_description: Optional[str] = None

class AdminMessageCreate(BaseModel):
    candidate_id: int
    chat_id: str
    sender: str
    sender_name: str
    text: str


class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: str
    experience_level: str
    salary_range: str
    location: str
    department: str

class JobResponse(BaseModel):
    id: int
    title: str
    description: str
    required_skills: str
    experience_level: str
    salary_range: Optional[str] = None
    location: str
    department: str
    status: str
    created_at: Optional[datetime] = None
    
    company_id: Optional[int] = None
    recruiter_id: Optional[int] = None
    company_logo: Optional[str] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    match_score: Optional[int] = None
    skills_gap: Optional[str] = None

    class Config:
        from_attributes = True


class LiveJobResponse(BaseModel):
    """Schema for real-time jobs fetched live from LinkedIn, Naukri, etc."""
    id: str                          # Stable hash ID e.g. 'a1b2c3d4e5f6g7h8'
    title: str
    company: str
    location: str
    experience: str
    work_mode: str
    skills: List[str]
    apply_url: str
    posted_date: str
    source: str                      # 'LinkedIn', 'Naukri', 'Foundit', etc.
    description: str
    match_score: int
    missing_skills: List[str]
    company_logo: Optional[str] = None
    is_saved: bool = False
    verification_score: Optional[int] = 0
    verification_status: Optional[str] = "Fully Verified"

    class Config:
        from_attributes = True

class ResumeResponse(BaseModel):
    id: int
    candidate_id: int
    resume_url: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ApplicationResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    resume_id: Optional[int]
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    job: JobResponse
    candidate: CandidateResponse
    resume: Optional[ResumeResponse] = None

    class Config:
        from_attributes = True

class ScreeningResultResponse(BaseModel):
    id: int
    application_id: int
    skill_match: float
    experience_match: float
    education_match: float
    project_match: float
    overall_score: float
    decision: str
    raw_reasoning: Optional[str]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class MCQQuestion(BaseModel):
    id: int
    question: str
    options: List[str]
    correct_option: int

class CodingChallenge(BaseModel):
    id: int
    title: str
    description: str
    template: str
    test_cases: List[dict]

class AssessmentResponse(BaseModel):
    id: int
    job_id: int
    title: str
    mcqs: str  # JSON list
    coding_challenges: str  # JSON list
    english_test: str  # JSON list
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AssessmentAttemptCreate(BaseModel):
    answers: str  # JSON String of answers

class AssessmentAttemptResponse(BaseModel):
    id: int
    application_id: int
    assessment_id: int
    status: str
    score: float
    passed: bool
    proctoring_violations: int
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class FraudLogCreate(BaseModel):
    event_type: str
    details: Optional[str] = None
    fraud_score: Optional[float] = 0.0

class FraudLogResponse(BaseModel):
    id: int
    attempt_id: int
    event_type: str
    screenshot_url: Optional[str]
    fraud_score: float
    details: Optional[str]
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True

class InterviewResponse(BaseModel):
    id: int
    application_id: int
    scheduled_at: Optional[datetime] = None
    status: str
    recording_url: Optional[str]
    transcript: Optional[str]
    questions: Optional[str]
    current_question_index: int

    class Config:
        from_attributes = True

class InterviewQuestionAnswer(BaseModel):
    answer: str

class InterviewResultResponse(BaseModel):
    id: int
    interview_id: int
    technical_score: float
    communication_score: float
    confidence_score: float
    thinking_score: float
    problem_solving_score: float
    fraud_score: float
    final_score: float
    report_summary: Optional[str]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CandidateRankingResponse(BaseModel):
    id: int
    application_id: int
    resume_score: float
    assessment_score: float
    interview_score: float
    fraud_penalty: float
    final_score: float
    rank: Optional[int]
    created_at: Optional[datetime] = None
    application: Optional[Any] = None

    class Config:
        from_attributes = True

class OfferResponse(BaseModel):
    id: int
    application_id: int
    offer_url: Optional[str]
    salary_offered: float
    status: str
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime]

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    read: bool
    type: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EmailNotificationResponse(BaseModel):
    id: int
    candidate_id: int
    sender: str
    recipient: str
    subject: str
    body: str
    sent_at: Optional[datetime] = None
    read: bool

    class Config:
        from_attributes = True

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCopilotRequest(BaseModel):
    message: str
    history: List[ChatMessage]

class ChatCopilotResponse(BaseModel):
    response: str
    actions: Optional[List[dict]] = None

class MessageCreate(BaseModel):
    chat_id: str
    text: str

class MessageResponse(BaseModel):
    id: int
    candidate_id: int
    chat_id: str
    sender: str
    sender_name: str
    text: str
    sent_at: Optional[datetime] = None
    read: bool

    class Config:
        from_attributes = True


class CompanyResponse(BaseModel):
    id: int
    name: str
    logo_url: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecruiterResponse(BaseModel):
    id: int
    name: str
    profile_url: Optional[str] = None
    company_id: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SavedJobResponse(BaseModel):
    id: int
    candidate_id: int
    job_id: int
    saved_at: datetime
    job: JobResponse

    class Config:
        from_attributes = True

class SearchHistoryResponse(BaseModel):
    id: int
    candidate_id: int
    query: str
    searched_at: datetime

    class Config:
        from_attributes = True

class SearchHistoryCreate(BaseModel):
    query: str

class SavedJobCreate(BaseModel):
    job_id: int

class CandidateJobsDashboardResponse(BaseModel):
    total_active_jobs: int
    new_jobs_today: int
    high_match_jobs: int
    remote_jobs: int
    internship_jobs: int
    fresher_jobs: int
    referral_opportunities: int
    company_career_jobs: int

class AdminJobsDashboardResponse(BaseModel):
    active_jobs: int
    jobs_collected_today: int
    hiring_posts_extracted: int
    duplicate_jobs_removed: int
    source_performance: List[dict]


class JobAgentLogResponse(BaseModel):
    id: int
    run_id: int
    message: str
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True


class JobAgentRunResponse(BaseModel):
    id: int
    candidate_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    logs: List[JobAgentLogResponse] = []

    class Config:
        from_attributes = True


class TelegramSourceCreate(BaseModel):
    channel_name: str
    active: Optional[bool] = True

class TelegramSourceResponse(BaseModel):
    id: int
    channel_name: str
    active: bool
    last_checked: Optional[datetime] = None

    class Config:
        from_attributes = True


class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str
    code: str


class AIMentorSessionCreateUpdate(BaseModel):
    title: str

class AIMentorSessionResponse(BaseModel):
    id: str
    user_id: int
    title: str
    metadata_json: Optional[Any] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AIMentorMessageResponse(BaseModel):
    id: str
    session_id: str
    user_id: int
    sender: str
    message: str
    metadata_json: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AIMentorChatRequest(BaseModel):
    message: str
    mode: Optional[str] = "tutor"  # "tutor" | "quiz" | "challenge" | "revision" | "interview"

class AIMentorChatResponse(BaseModel):
    response: str
    session_id: str

class AIMentorStudyPlanRequest(BaseModel):
    duration: str  # "7-day" | "30-day" | "90-day"
    title: Optional[str] = None

class AIMentorStudyPlanResponse(BaseModel):
    id: str
    user_id: int
    duration: str
    title: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class AIMentorInsightResponse(BaseModel):
    id: str
    user_id: int
    insight_type: str
    title: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True

class AIMentorArtifactResponse(BaseModel):
    id: str
    user_id: int
    artifact_type: str
    title: str
    content: str
    version: int
    metadata_json: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AIMentorArtifactCreate(BaseModel):
    artifact_type: str
    title: str
    content: str
    metadata_json: Optional[Any] = None

class AIMentorCourseProgressInfo(BaseModel):
    course_id: str
    title: str
    progress: float
    status: str

class AIMentorStatsResponse(BaseModel):
    health_score: float
    health_status: str  # "At Risk" | "Improving" | "Good Progress" | "Excellent"
    strengths: List[str]
    weaknesses: List[str]
    next_best_actions: List[str]
    estimated_time: str
    xp: int
    level: int
    streak: int
    weekly_progress: float
    courses_in_progress: int
    completed_courses: int
    completed_lessons_count: int
    avg_quiz_score: float
    upcoming_assessments: List[str]
    insights: List[AIMentorInsightResponse]
    enrolled_courses: List[AIMentorCourseProgressInfo]
    career_goal: str
    target_role: Optional[str] = "Frontend Developer"
    target_level: Optional[str] = "Mid-Level"
    hours_learned: float
    completed_certs: int
    monthly_progress: float
    risk_score: float
    current_roadmap_stage: str
    weekly_goal_progress: float
    agent_status: str

class UserGoalUpdate(BaseModel):
    career_goal: str
    target_role: Optional[str] = "Frontend Developer"
    target_level: Optional[str] = "Mid-Level"

class AIMentorRiskResponse(BaseModel):
    risk_level: str  # "Low" | "Medium" | "High"
    reason: str


class AIMentorAnalyticsResponse(BaseModel):
    average_health_score: float
    difficult_topics: List[dict]
    most_requested_actions: List[dict]
    total_artifacts_generated: int
    engagement_rate: float


# MCP Chat schemas (imported from mcp_schemas for router compatibility)
from app.schemas.mcp_schemas import (
    MCPChatRequest,
    MCPChatResponse,
    ActionCard,
    HAQItemResponse,
    HAQCompleteRequest,
    MCPChatMessage,
    MCPChatSessionResponse,
    MCPChatSessionUpdate,
    MCPChatSessionListResponse
)




