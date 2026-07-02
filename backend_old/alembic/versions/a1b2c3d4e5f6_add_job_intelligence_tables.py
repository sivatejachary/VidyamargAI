"""Add job intelligence tables

Revision ID: a1b2c3d4e5f6
Revises: d5f303fbe12b
Create Date: 2026-06-23 12:00:00.000000

Adds the full job intelligence schema:
  companies, job_sources, jobs, candidate_agents,
  candidate_agent_preferences, agent_runs, agent_actions, agent_notifications,
  matches, recommendations, applications, application_events,
  interview_preparations, skill_gap_analysis, career_insights,
  market_intelligence, analytics_events
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = 'd5f303fbe12b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── companies ──────────────────────────────────────────────────────────────
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('sub_industry', sa.String(length=100), nullable=True),
        sa.Column('company_size', sa.String(length=50), nullable=True),
        sa.Column('founded_year', sa.Integer(), nullable=True),
        sa.Column('headquarters', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('glassdoor_rating', sa.Float(), nullable=True),
        sa.Column('glassdoor_reviews', sa.Integer(), nullable=True),
        sa.Column('trust_score', sa.Float(), server_default='0.5'),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('is_blacklisted', sa.Boolean(), server_default='false'),
        sa.Column('blacklist_reason', sa.String(length=255), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('embedding_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name', name='uq_company_normalized_name'),
    )
    op.create_index('ix_companies_id', 'companies', ['id'], unique=False)
    op.create_index('ix_companies_name', 'companies', ['name'], unique=False)
    op.create_index('ix_companies_normalized_name', 'companies', ['normalized_name'], unique=False)
    op.create_index('ix_companies_domain', 'companies', ['domain'], unique=False)
    op.create_index('ix_companies_industry', 'companies', ['industry'], unique=False)
    op.create_index('idx_company_industry', 'companies', ['industry'], unique=False)
    op.create_index('idx_company_trust', 'companies', ['trust_score'], unique=False)

    # ── job_sources ────────────────────────────────────────────────────────────
    op.create_table(
        'job_sources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('priority', sa.Integer(), server_default='5'),
        sa.Column('rate_limit_rpm', sa.Integer(), server_default='60'),
        sa.Column('rate_limit_daily', sa.Integer(), server_default='10000'),
        sa.Column('health_score', sa.Float(), server_default='1.0'),
        sa.Column('last_success_at', sa.DateTime(), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), server_default='0'),
        sa.Column('total_jobs_discovered', sa.BigInteger(), server_default='0'),
        sa.Column('total_jobs_accepted', sa.BigInteger(), server_default='0'),
        sa.Column('total_jobs_rejected', sa.BigInteger(), server_default='0'),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_job_sources_id', 'job_sources', ['id'], unique=False)
    op.create_index('idx_jobsource_active_priority', 'job_sources', ['is_active', 'priority'], unique=False)

    # ── jobs ───────────────────────────────────────────────────────────────────
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=500), nullable=True),
        sa.Column('source_id', sa.Integer(), nullable=True),
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('title_normalized', sa.String(length=500), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('description_summary', sa.Text(), nullable=True),
        sa.Column('apply_url', sa.String(length=1000), nullable=True),
        sa.Column('job_url', sa.String(length=1000), nullable=True),
        sa.Column('location', sa.String(length=500), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('is_remote', sa.Boolean(), server_default='false'),
        sa.Column('is_hybrid', sa.Boolean(), server_default='false'),
        sa.Column('role_category', sa.String(length=100), nullable=True),
        sa.Column('role_sub_category', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('seniority', sa.String(length=50), nullable=True),
        sa.Column('employment_type', sa.String(length=50), nullable=True),
        sa.Column('work_mode', sa.String(length=50), nullable=True),
        sa.Column('required_skills', sa.JSON(), nullable=True),
        sa.Column('preferred_skills', sa.JSON(), nullable=True),
        sa.Column('skill_graph', sa.JSON(), nullable=True),
        sa.Column('salary_min', sa.Float(), nullable=True),
        sa.Column('salary_max', sa.Float(), nullable=True),
        sa.Column('salary_currency', sa.String(length=10), server_default='USD'),
        sa.Column('salary_period', sa.String(length=20), server_default='yearly'),
        sa.Column('salary_raw', sa.String(length=255), nullable=True),
        sa.Column('experience_min_years', sa.Float(), nullable=True),
        sa.Column('experience_max_years', sa.Float(), nullable=True),
        sa.Column('trust_score', sa.Float(), server_default='0.5'),
        sa.Column('quality_score', sa.Float(), server_default='0.5'),
        sa.Column('freshness_score', sa.Float(), server_default='1.0'),
        sa.Column('spam_score', sa.Float(), server_default='0.0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('is_duplicate', sa.Boolean(), server_default='false'),
        sa.Column('duplicate_of_id', sa.Integer(), nullable=True),
        sa.Column('rejection_reason', sa.String(length=255), nullable=True),
        sa.Column('embedding_id', sa.String(length=100), nullable=True),
        sa.Column('embedding_version', sa.Integer(), server_default='0'),
        sa.Column('posted_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('discovered_at', sa.DateTime(), nullable=True),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('trust_score >= 0.0 AND trust_score <= 1.0', name='chk_job_trust_range'),
        sa.CheckConstraint('quality_score >= 0.0 AND quality_score <= 1.0', name='chk_job_quality_range'),
        sa.CheckConstraint('spam_score >= 0.0 AND spam_score <= 1.0', name='chk_job_spam_range'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['duplicate_of_id'], ['jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_id'], ['job_sources.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_jobs_id', 'jobs', ['id'], unique=False)
    op.create_index('ix_jobs_external_id', 'jobs', ['external_id'], unique=False)
    op.create_index('ix_jobs_title', 'jobs', ['title'], unique=False)
    op.create_index('ix_jobs_company_name', 'jobs', ['company_name'], unique=False)
    op.create_index('ix_jobs_is_active', 'jobs', ['is_active'], unique=False)
    op.create_index('ix_jobs_posted_at', 'jobs', ['posted_at'], unique=False)
    op.create_index('ix_jobs_discovered_at', 'jobs', ['discovered_at'], unique=False)
    op.create_index('idx_job_active_quality', 'jobs', ['is_active', 'quality_score'], unique=False)
    op.create_index('idx_job_active_trust', 'jobs', ['is_active', 'trust_score'], unique=False)
    op.create_index('idx_job_active_fresh', 'jobs', ['is_active', 'freshness_score'], unique=False)
    op.create_index('idx_job_role_seniority', 'jobs', ['role_category', 'seniority'], unique=False)
    op.create_index('idx_job_country_city', 'jobs', ['country', 'city'], unique=False)
    op.create_index('idx_job_company_posted', 'jobs', ['company_id', 'posted_at'], unique=False)
    op.create_index('idx_job_external_source', 'jobs', ['external_id', 'source_id'], unique=False)

    # ── candidate_agents ───────────────────────────────────────────────────────
    op.create_table(
        'candidate_agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='active'),
        sa.Column('career_dna', sa.JSON(), nullable=True),
        sa.Column('skill_graph', sa.JSON(), nullable=True),
        sa.Column('career_graph', sa.JSON(), nullable=True),
        sa.Column('industry_dna', sa.JSON(), nullable=True),
        sa.Column('target_roles', sa.JSON(), nullable=True),
        sa.Column('target_locations', sa.JSON(), nullable=True),
        sa.Column('target_salary_min', sa.Float(), nullable=True),
        sa.Column('target_salary_max', sa.Float(), nullable=True),
        sa.Column('target_salary_currency', sa.String(length=10), server_default='USD'),
        sa.Column('work_mode_preference', sa.String(length=50), server_default='any'),
        sa.Column('employment_type_preference', sa.String(length=50), server_default='full_time'),
        sa.Column('min_match_score', sa.Float(), server_default='60.0'),
        sa.Column('last_discovery_at', sa.DateTime(), nullable=True),
        sa.Column('last_match_at', sa.DateTime(), nullable=True),
        sa.Column('next_scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('total_jobs_discovered', sa.Integer(), server_default='0'),
        sa.Column('total_jobs_matched', sa.Integer(), server_default='0'),
        sa.Column('total_applications', sa.Integer(), server_default='0'),
        sa.Column('embedding_version', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id'),
    )
    op.create_index('ix_candidate_agents_id', 'candidate_agents', ['id'], unique=False)
    op.create_index('ix_candidate_agents_candidate_id', 'candidate_agents', ['candidate_id'], unique=False)
    op.create_index('idx_agent_status_next', 'candidate_agents', ['status', 'next_scheduled_at'], unique=False)

    # ── candidate_agent_preferences ────────────────────────────────────────────
    op.create_table(
        'candidate_agent_preferences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('auto_discover', sa.Boolean(), server_default='true'),
        sa.Column('discovery_frequency_hours', sa.Integer(), server_default='6'),
        sa.Column('notify_new_matches', sa.Boolean(), server_default='true'),
        sa.Column('notify_application_updates', sa.Boolean(), server_default='true'),
        sa.Column('notify_skill_gaps', sa.Boolean(), server_default='true'),
        sa.Column('notify_market_changes', sa.Boolean(), server_default='false'),
        sa.Column('min_match_score_notify', sa.Float(), server_default='70.0'),
        sa.Column('excluded_companies', sa.JSON(), nullable=True),
        sa.Column('excluded_keywords', sa.JSON(), nullable=True),
        sa.Column('preferred_company_sizes', sa.JSON(), nullable=True),
        sa.Column('preferred_industries', sa.JSON(), nullable=True),
        sa.Column('open_to_relocation', sa.Boolean(), server_default='false'),
        sa.Column('max_commute_km', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id'),
    )
    op.create_index('ix_candidate_agent_preferences_id', 'candidate_agent_preferences', ['id'], unique=False)

    # ── agent_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        'agent_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('run_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='running'),
        sa.Column('trigger', sa.String(length=50), server_default='scheduled'),
        sa.Column('jobs_discovered', sa.Integer(), server_default='0'),
        sa.Column('jobs_matched', sa.Integer(), server_default='0'),
        sa.Column('jobs_rejected', sa.Integer(), server_default='0'),
        sa.Column('recommendations_generated', sa.Integer(), server_default='0'),
        sa.Column('skill_gaps_updated', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('llm_cost_usd', sa.Float(), server_default='0.0'),
        sa.Column('embedding_cost_usd', sa.Float(), server_default='0.0'),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['candidate_agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_runs_id', 'agent_runs', ['id'], unique=False)
    op.create_index('idx_agentrun_agent_status', 'agent_runs', ['agent_id', 'status'], unique=False)
    op.create_index('idx_agentrun_candidate_started', 'agent_runs', ['candidate_id', 'started_at'], unique=False)

    # ── agent_actions ──────────────────────────────────────────────────────────
    op.create_table(
        'agent_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=100), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='completed'),
        sa.Column('input_summary', sa.Text(), nullable=True),
        sa.Column('output_summary', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['agent_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_actions_id', 'agent_actions', ['id'], unique=False)
    op.create_index('idx_agentaction_run', 'agent_actions', ['run_id'], unique=False)
    op.create_index('idx_agentaction_candidate', 'agent_actions', ['candidate_id'], unique=False)

    # ── agent_notifications ────────────────────────────────────────────────────
    op.create_table(
        'agent_notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('notification_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('action_url', sa.String(length=500), nullable=True),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('is_read', sa.Boolean(), server_default='false'),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='normal'),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['candidate_agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agent_notifications_id', 'agent_notifications', ['id'], unique=False)
    op.create_index('ix_agent_notifications_is_read', 'agent_notifications', ['is_read'], unique=False)
    op.create_index('idx_agentnotif_candidate_unread', 'agent_notifications', ['candidate_id', 'is_read'], unique=False)
    op.create_index('idx_agentnotif_created', 'agent_notifications', ['created_at'], unique=False)

    # ── matches ────────────────────────────────────────────────────────────────
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('agent_run_id', sa.Integer(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('semantic_score', sa.Float(), server_default='0.0'),
        sa.Column('skill_score', sa.Float(), server_default='0.0'),
        sa.Column('experience_score', sa.Float(), server_default='0.0'),
        sa.Column('education_score', sa.Float(), server_default='0.0'),
        sa.Column('location_score', sa.Float(), server_default='0.0'),
        sa.Column('salary_score', sa.Float(), server_default='0.0'),
        sa.Column('career_progression_score', sa.Float(), server_default='0.0'),
        sa.Column('seniority_score', sa.Float(), server_default='0.0'),
        sa.Column('match_reasons', sa.JSON(), nullable=True),
        sa.Column('missing_skills', sa.JSON(), nullable=True),
        sa.Column('skill_gap_severity', sa.String(length=20), server_default='none'),
        sa.Column('career_growth_score', sa.Float(), server_default='0.0'),
        sa.Column('match_explanation', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='new'),
        sa.Column('is_seen', sa.Boolean(), server_default='false'),
        sa.Column('seen_at', sa.DateTime(), nullable=True),
        sa.Column('is_saved', sa.Boolean(), server_default='false'),
        sa.Column('saved_at', sa.DateTime(), nullable=True),
        sa.Column('is_hidden', sa.Boolean(), server_default='false'),
        sa.Column('user_reaction', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.CheckConstraint('overall_score >= 0.0 AND overall_score <= 100.0', name='chk_match_score_range'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id', 'job_id', name='uq_match_candidate_job'),
    )
    op.create_index('ix_matches_id', 'matches', ['id'], unique=False)
    op.create_index('ix_matches_overall_score', 'matches', ['overall_score'], unique=False)
    op.create_index('ix_matches_status', 'matches', ['status'], unique=False)
    op.create_index('idx_match_candidate_score', 'matches', ['candidate_id', 'overall_score'], unique=False)
    op.create_index('idx_match_candidate_status', 'matches', ['candidate_id', 'status'], unique=False)
    op.create_index('idx_match_candidate_created', 'matches', ['candidate_id', 'created_at'], unique=False)

    # ── recommendations ────────────────────────────────────────────────────────
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('rec_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('entity_data', sa.JSON(), nullable=True),
        sa.Column('score', sa.Float(), server_default='0.0'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_seen', sa.Boolean(), server_default='false'),
        sa.Column('is_actioned', sa.Boolean(), server_default='false'),
        sa.Column('actioned_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recommendations_id', 'recommendations', ['id'], unique=False)
    op.create_index('idx_rec_candidate_type', 'recommendations', ['candidate_id', 'rec_type'], unique=False)
    op.create_index('idx_rec_candidate_seen', 'recommendations', ['candidate_id', 'is_seen'], unique=False)

    # ── applications ───────────────────────────────────────────────────────────
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='saved'),
        sa.Column('applied_via', sa.String(length=100), nullable=True),
        sa.Column('resume_version_id', sa.Integer(), nullable=True),
        sa.Column('cover_letter', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('saved_at', sa.DateTime(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('resume_viewed_at', sa.DateTime(), nullable=True),
        sa.Column('shortlisted_at', sa.DateTime(), nullable=True),
        sa.Column('first_interview_at', sa.DateTime(), nullable=True),
        sa.Column('offer_received_at', sa.DateTime(), nullable=True),
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(), nullable=True),
        sa.Column('interview_rounds', sa.Integer(), server_default='0'),
        sa.Column('interview_notes', sa.Text(), nullable=True),
        sa.Column('offer_salary', sa.Float(), nullable=True),
        sa.Column('offer_currency', sa.String(length=10), nullable=True),
        sa.Column('rejection_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['match_id'], ['matches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resume_version_id'], ['candidate_resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id', 'job_id', name='uq_application_candidate_job'),
    )
    op.create_index('ix_applications_id', 'applications', ['id'], unique=False)
    op.create_index('ix_applications_status', 'applications', ['status'], unique=False)
    op.create_index('idx_application_candidate_status', 'applications', ['candidate_id', 'status'], unique=False)
    op.create_index('idx_application_candidate_created', 'applications', ['candidate_id', 'created_at'], unique=False)

    # ── application_events ─────────────────────────────────────────────────────
    op.create_table(
        'application_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=True),
        sa.Column('actor', sa.String(length=50), server_default='user'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_application_events_id', 'application_events', ['id'], unique=False)
    op.create_index('idx_appevent_application', 'application_events', ['application_id'], unique=False)

    # ── interview_preparations ─────────────────────────────────────────────────
    op.create_table(
        'interview_preparations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('application_id', sa.Integer(), nullable=True),
        sa.Column('company_analysis', sa.JSON(), nullable=True),
        sa.Column('technical_questions', sa.JSON(), nullable=True),
        sa.Column('hr_questions', sa.JSON(), nullable=True),
        sa.Column('behavioral_questions', sa.JSON(), nullable=True),
        sa.Column('culture_fit_questions', sa.JSON(), nullable=True),
        sa.Column('study_topics', sa.JSON(), nullable=True),
        sa.Column('estimated_prep_hours', sa.Float(), nullable=True),
        sa.Column('difficulty_level', sa.String(length=50), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_interview_preparations_id', 'interview_preparations', ['id'], unique=False)
    op.create_index('idx_interviewprep_candidate_job', 'interview_preparations', ['candidate_id', 'job_id'], unique=False)

    # ── skill_gap_analysis ─────────────────────────────────────────────────────
    op.create_table(
        'skill_gap_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('analysis_type', sa.String(length=50), server_default='overall'),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('current_skills', sa.JSON(), nullable=True),
        sa.Column('required_skills', sa.JSON(), nullable=True),
        sa.Column('missing_skills', sa.JSON(), nullable=True),
        sa.Column('skill_scores', sa.JSON(), nullable=True),
        sa.Column('learning_roadmap', sa.JSON(), nullable=True),
        sa.Column('overall_gap_score', sa.Float(), server_default='0.0'),
        sa.Column('estimated_upskill_months', sa.Float(), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_skill_gap_analysis_id', 'skill_gap_analysis', ['id'], unique=False)
    op.create_index('idx_skillgap_candidate', 'skill_gap_analysis', ['candidate_id'], unique=False)

    # ── career_insights ────────────────────────────────────────────────────────
    op.create_table(
        'career_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('insight_category', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), server_default='0.8'),
        sa.Column('is_positive', sa.Boolean(), nullable=True),
        sa.Column('actionable_steps', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_career_insights_id', 'career_insights', ['id'], unique=False)
    op.create_index('idx_careerinsight_candidate', 'career_insights', ['candidate_id', 'created_at'], unique=False)

    # ── market_intelligence ────────────────────────────────────────────────────
    op.create_table(
        'market_intelligence',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_category', sa.String(length=100), nullable=False),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('seniority', sa.String(length=50), nullable=True),
        sa.Column('active_job_count', sa.Integer(), server_default='0'),
        sa.Column('avg_salary_min', sa.Float(), nullable=True),
        sa.Column('avg_salary_max', sa.Float(), nullable=True),
        sa.Column('salary_currency', sa.String(length=10), server_default='USD'),
        sa.Column('demand_trend', sa.String(length=20), server_default='stable'),
        sa.Column('demand_score', sa.Float(), server_default='0.5'),
        sa.Column('top_required_skills', sa.JSON(), nullable=True),
        sa.Column('top_companies_hiring', sa.JSON(), nullable=True),
        sa.Column('emerging_skills', sa.JSON(), nullable=True),
        sa.Column('average_time_to_fill_days', sa.Float(), nullable=True),
        sa.Column('competition_score', sa.Float(), server_default='0.5'),
        sa.Column('snapshot_date', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_market_intelligence_id', 'market_intelligence', ['id'], unique=False)
    op.create_index('ix_market_intelligence_role_category', 'market_intelligence', ['role_category'], unique=False)
    op.create_index('idx_market_role_country_date', 'market_intelligence', ['role_category', 'country', 'snapshot_date'], unique=False)

    # ── analytics_events ───────────────────────────────────────────────────────
    op.create_table(
        'analytics_events',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=True),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analytics_events_id', 'analytics_events', ['id'], unique=False)
    op.create_index('ix_analytics_events_event_type', 'analytics_events', ['event_type'], unique=False)
    op.create_index('idx_analytics_candidate_event', 'analytics_events', ['candidate_id', 'event_type'], unique=False)
    op.create_index('idx_analytics_created', 'analytics_events', ['created_at'], unique=False)

    # ── seed default job sources ───────────────────────────────────────────────
    op.execute("""
        INSERT INTO job_sources (name, display_name, source_type, base_url, is_active, priority, rate_limit_rpm, config)
        VALUES
            ('serper_jobs', 'Google Jobs (Serper)', 'api', 'https://google.serper.dev/jobs', true, 1, 30, '{"requires_key": true}'),
            ('indeed_rss', 'Indeed RSS', 'rss', 'https://www.indeed.com/rss', true, 2, 20, '{}'),
            ('remoteok', 'RemoteOK', 'api', 'https://remoteok.com/api', true, 3, 10, '{}'),
            ('wellfound', 'Wellfound (AngelList)', 'api', 'https://api.wellfound.com', false, 4, 5, '{"requires_key": true}'),
            ('naukri_partner', 'Naukri Partner API', 'partner', 'https://www.naukri.com', false, 5, 5, '{"requires_key": true}')
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table('analytics_events')
    op.drop_table('market_intelligence')
    op.drop_table('career_insights')
    op.drop_table('skill_gap_analysis')
    op.drop_table('interview_preparations')
    op.drop_table('application_events')
    op.drop_table('applications')
    op.drop_table('recommendations')
    op.drop_table('matches')
    op.drop_table('agent_notifications')
    op.drop_table('agent_actions')
    op.drop_table('agent_runs')
    op.drop_table('candidate_agent_preferences')
    op.drop_table('candidate_agents')
    op.drop_table('jobs')
    op.drop_table('job_sources')
    op.drop_table('companies')
