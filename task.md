# Auto Apply Agent — Build Tasks

## Layer 1 — DB Models
- [x] `models/auto_apply_models.py` — all 9 new tables
- [x] Extend `UserConsent` in `models/models.py` (+revoked_at, +metadata_json)
- [x] Extend `CandidateResume` (+resume_type) and `UserPreference` (+auto_apply_* cols)

## Layer 2 — Core Services
- [x] `services/auto_apply/credential_vault.py`
- [x] `services/auto_apply/consent_service.py`
- [x] `services/auto_apply/audit_service.py`
- [x] `services/auto_apply/platform_health_service.py`
- [x] `services/auto_apply/platform_rate_limiter.py`
- [x] `services/auto_apply/requirements_validator.py`
- [x] `services/auto_apply/resume_match_agent.py`
- [x] `services/auto_apply/cover_letter_generator.py`
- [x] `services/auto_apply/screening_answer_engine.py`
- [x] `services/auto_apply/application_queue.py`

## Layer 3 — Platform Adapters
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
