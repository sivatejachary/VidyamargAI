"""
MCP Schemas — request/response models for the /mcp/chat endpoint.
"""
from typing import Optional, Literal, Any
from pydantic import BaseModel


from datetime import datetime

class MCPChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class MCPChatRequest(BaseModel):
    message: str
    mode: Literal["resume", "skill-lab", "job-agent", "general"] = "general"
    history: list[MCPChatMessage] = []
    context_hint: Optional[str] = None  # Extra context from the frontend widget
    session_id: Optional[str] = None


class MCPChatSessionResponse(BaseModel):
    id: str
    title: str
    mode: str
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MCPChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class MCPChatSessionListResponse(BaseModel):
    sessions: list[MCPChatSessionResponse]
    total_count: int
    page: int
    pages: int



class ActionCard(BaseModel):
    type: Literal["course", "job", "resume_tip", "career_path", "haq"]
    id: Optional[Any] = None
    title: str
    subtitle: str = ""
    action_label: str = "View"
    action_href: str = "#"
    meta: dict = {}


class HAQCard(BaseModel):
    callback_key: str
    action_type: str
    title: str
    description: str


class MCPChatResponse(BaseModel):
    response: str
    action_cards: list[ActionCard] = []
    haq_required: bool = False
    haq_item: Optional[HAQCard] = None
    memory_updated: bool = False
    actions: list[dict] = []  # backward compat with old /chat/copilot
    intent: Optional[str] = None
    agent_used: Optional[str] = None
    session_id: Optional[str] = None


class HAQItemResponse(BaseModel):
    id: int
    action_type: str
    title: str
    description: Optional[str]
    status: str
    callback_key: str
    created_at: str
    expires_at: Optional[str]


class HAQCompleteRequest(BaseModel):
    human_input: dict = {}
