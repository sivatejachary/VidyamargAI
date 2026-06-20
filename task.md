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
- [x] Backend Database Models & Migrations
  - [x] Add `MCPChatSession` and `MCPChatMessage` SQLAlchemy models to `backend/app/models/models.py`
  - [x] Add table creation SQL schema to `backend/app/main.py`
- [x] Admin Metrics Endpoint inside `backend/app/api/endpoints.py`
- [x] Alerting Rules Engine inside `backend/app/services/alerting.py`
- [x] Hook background worker startups in `backend/app/main.py`
- [x] Write and execute the 5 simulation & verification scripts inside `backend/scratch/`

## Phase 7 — Performance Optimizations and Resiliency Fixes
- [x] Database: Ensure `updated_at` column in `courses` table and apply migration
- [x] Caching: Implement curriculum caching and N+1 query optimization in `get_course_curriculum`
- [x] Caching: Implement resume analysis caching in `resume_cache.py` and integrate it into `/candidates/resume/analyze`
- [x] Caching: Invalidate resume analysis cache in `update_candidate_profile`, `upload_resume`, and `delete_candidate_resume`
- [x] AI: Implement resilient Gemini API caller with auto-fallback to NVIDIA API
- [x] Cache Serializer: Add custom datetime serialization support to `set_cached_mentor_profile`
- [x] Verification: Write and run verification tests

## Phase 8 — Advanced Security, JWT Refresh, Redis Caching, Router Refactoring, CI/CD
- [x] Security: Untrack sensitive files (`.env`, session files) from git history
- [x] Security: Require `SECRET_KEY` env var check on server startup
- [x] Security: Validate Railway environment variables
- [x] JWT Refresh: Implement 15-minute access token + 7-day refresh token flow
- [x] JWT Refresh: Store SHA-256 hashes of refresh tokens in database
- [x] JWT Refresh: Implement token refresh and logout invalidation endpoints
- [x] Redis Caching: Add caching for `jobs:pool`, `skill_gap`, `study_plan`, and `candidate_profile`
- [x] Router Refactoring: Split monolithic `endpoints.py` into 14 micro-routers under `backend/app/api/routers/`
- [x] Router Refactoring: Maintain backward compatibility for helper exports and testing mocks
- [x] CI/CD: Add GitHub Actions verification pipeline with `detect-secrets` scan
- [x] Verification: Fix all collection, import, and NameError issues and verify green across the entire test suite



