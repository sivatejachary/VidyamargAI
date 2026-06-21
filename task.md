# Auto Apply Agent — Build# Task List

- [x] 1. Database schema and models updates
    - [x] Add columns to `Candidate` class in `backend/app/models/models.py`
    - [x] Add migrations to `init_db_safely()` in `backend/app/main.py`
    - [x] Add fields to `CandidateResponse` and `CandidateProfileUpdate` in `backend/app/schemas/schemas.py`
- [x] 2. Update backend processing logic & WebSockets
    - [x] Update `/candidates/resume/upload` endpoint in `backend/app/api/routers/resume.py` to support background task initialization
    - [x] Update parsing pipeline `run_resume_parsing_agent` in `backend/app/services/orchestrator.py` to save steps/progress and broadcast via WebSocket to `candidate_{candidate_id}`
    - [x] Separate job discovery matching task from resume ingestion completion
- [x] 3. Update frontend resume builder page
    - [x] Add `useWebSockets` hook with `candidate_{candidate_id}` connection
    - [x] Handle real-time WebSocket progress/failure events
    - [x] Implement adaptive fallback polling
    - [x] Build the new **Resume Analysis** dashboard section rendering extracted summary, experience, projects, and education
- [x] 4. Update frontend profile page
    - [x] Add `summary` and `projects` states and input/display sections
    - [x] Wire up with `apiService.updateProfile`
- [x] 5. Verification and tests
    - [x] Run backend tests
    - [x] Verify UI updates dynamically
- [x] `services/auto_apply/adapters/__init__.py` (registry + detect_platform)
- [x] `services/auto_apply/adapters/base.py`
- [x] 19 adapter files

## Layer 4 — Config
- [x] `config/platform_rate_limits.json`
- [x] `core/config.py` (new settings)
- [x] `requirements.txt` (+cryptography, +langgraph-checkpoint-sqlite)

## Layer 5 — API
- [x] `schemas/auto_apply_schemas.py`
- [x] `api/routers/auto_apply.py`
- [x] Wire into `api/endpoints.py`

## Layer 6 — LangGraph Agent
- [x] `agents/auto_apply_agent.py`

## Layer 7 — Migration
- [x] Alembic migration file

## Layer 8 — Tests
- [x] `tests/test_auto_apply.py`
