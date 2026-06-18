# VidyaMarg AI OS — Task Tracker

## Phase 1 — OS Kernel

### 1C. DB Models
- [x] Create `backend/app/models/mcp_models.py`
  - [x] `ToolPermission` table
  - [x] `AgentActivity` table
  - [x] `HumanActionItem` table
  - [x] `AgentMemory` table
  - [x] `VectorMemoryChunk` table (pgvector)
- [x] Import mcp_models in main.py / models __init__

### 1A. Agent Registry
- [x] Create `backend/app/agents/agent_registry.py`

### 1B. MCP Tool Servers
- [x] Create `backend/app/mcp/__init__.py`
- [x] Create `backend/app/mcp/base.py`
- [x] Create `backend/app/mcp/resume_tools.py`
- [x] Create `backend/app/mcp/skilllab_tools.py`
- [x] Create `backend/app/mcp/job_tools.py`

### 1E. Human Action Queue
- [x] Create `backend/app/services/human_action_queue.py`
- [x] Add HAQ endpoints to `api/endpoints.py`
- [x] Create `frontend/components/HumanActionQueue.tsx`

### 1D. Supervisor Agent
- [x] Create `backend/app/agents/supervisor_agent.py`

## Phase 2 — Memory Layer
- [x] Create `backend/app/services/agent_memory.py`
- [x] Create `backend/app/services/vector_memory.py`
- [x] Add pgvector migration

## Phase 3 — Intelligence Services
- [x] Create `backend/app/services/skill_gap_graph.py`
- [x] Create `backend/app/services/learning_health.py`
- [x] Create `backend/app/services/event_bus.py`
- [x] Create `backend/app/services/agent_activity_feed.py`
- [x] Create `backend/app/agents/cost_controller.py`

## Phase 4 — Job Agent Split
- [x] Create `backend/app/agents/job_supervisor_agent.py`
- [x] Create `backend/app/agents/job_discovery_agent.py`
- [x] Create `backend/app/agents/job_match_agent.py`
- [x] Create `backend/app/agents/application_agent.py`
- [x] Create `backend/app/agents/status_agent.py`
- [x] Create `backend/app/agents/company_research_agent.py`
- [x] Create `backend/app/agents/salary_agent.py`

## Phase 5 — Action Cards + Frontend + Wire
- [x] Create `backend/app/schemas/mcp_schemas.py`
- [x] Create `backend/app/services/action_card_parser.py`
- [x] Wire `POST /mcp/chat` endpoint in `api/endpoints.py`
- [x] Create `frontend/components/AIActionCard.tsx`
- [x] Create `frontend/components/AgentActivityFeed.tsx`
- [x] Update `frontend/components/MCPChat.tsx` → use `/mcp/chat`
- [x] Update `frontend/app/candidate/chat/page.tsx` → activity feed panel
- [x] Fix `ExploreCourses.tsx` — roadmap matching + grid
- [x] Fix `MyLearning.tsx` — 3-per-row, remove stat cards

## Phase 6 — Production Readiness, Auditing & Fallback

- [x] DB Models: Add `AgentHealth`, `MCPAuditLog`, `DeadLetterJob`, and `CircuitBreakerState` to `backend/app/models/mcp_models.py`
- [x] Explicit Tool Auditing & Async Batch Persistence in `backend/app/services/mcp_audit.py`
- [x] Centralized Circuit Breaker with Redis Cache in `backend/app/mcp/base.py`
- [x] Decorate MCP Tools in `resume_tools.py`, `skilllab_tools.py`, and `job_tools.py`
- [x] Postgres-Backed Task Queue Fallback with ThreadPoolExecutor limit inside `backend/app/core/queue.py`
- [x] Admin Metrics Endpoint inside `backend/app/api/endpoints.py`
- [x] Alerting Rules Engine inside `backend/app/services/alerting.py`
- [x] Hook background worker startups in `backend/app/main.py`
- [x] Write and execute the 5 simulation & verification scripts inside `backend/scratch/`
