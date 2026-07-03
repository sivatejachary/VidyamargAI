"""
Initial schema migration
Revision ID: 0001
Revises: None
Create Date: 2026-07-03 05:22:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # 1. Companies Table
    # ---------------------------------------------------------------------------
    op.create_table(
        'companies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('sub_industry', sa.String(length=100), nullable=True),
        sa.Column('company_size', sa.String(length=50), nullable=True),
        sa.Column('headquarters', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('linkedin_url', sa.String(length=500), nullable=True),
        sa.Column('glassdoor_rating', sa.REAL(), nullable=True),
        sa.Column('trust_score', sa.REAL(), nullable=True, server_default='0.5'),
        sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_blacklisted', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('blacklist_reason', sa.String(length=255), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('embedding_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name', name='uq_company_normalized_name')
    )
    op.create_index('idx_company_industry', 'companies', ['industry'])
    op.create_index('idx_company_trust', 'companies', ['trust_score'])

    # ---------------------------------------------------------------------------
    # 2. Job Sources Table
    # ---------------------------------------------------------------------------
    op.create_table(
        'job_sources',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('base_url', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('priority', sa.Integer(), nullable=True, server_default='5'),
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('rate_limit_daily', sa.Integer(), nullable=True, server_default='10000'),
        sa.Column('health_score', sa.REAL(), nullable=True, server_default='1.0'),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_jobs_discovered', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('total_jobs_accepted', sa.BigInteger(), nullable=True, server_default='0'),
        sa.Column('config', sa.JSON(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_jobsource_active_priority', 'job_sources', ['is_active', 'priority'])

    # ---------------------------------------------------------------------------
    # 3. Jobs Table (Partitioned by Range of created_at)
    # We must run this using raw SQL to create the partitioned table and partitions.
    # ---------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE jobs (
            id SERIAL,
            external_id VARCHAR(500) NOT NULL,
            source_id INT REFERENCES job_sources(id) ON DELETE SET NULL,
            company_id INT REFERENCES companies(id) ON DELETE SET NULL,
            title VARCHAR(500) NOT NULL,
            title_normalized VARCHAR(500) NOT NULL,
            company_name VARCHAR(255) NOT NULL,
            description TEXT,
            description_summary TEXT,
            apply_url VARCHAR(1000),
            job_url VARCHAR(1000),
            location VARCHAR(500),
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(10) DEFAULT 'IN',
            is_remote BOOLEAN DEFAULT FALSE,
            is_hybrid BOOLEAN DEFAULT FALSE,
            work_mode VARCHAR(50),
            role_category VARCHAR(100),
            role_sub_category VARCHAR(100),
            industry VARCHAR(100),
            seniority VARCHAR(50),
            employment_type VARCHAR(50),
            required_skills JSONB DEFAULT '[]'::jsonb,
            preferred_skills JSONB DEFAULT '[]'::jsonb,
            skill_graph JSONB DEFAULT '{}'::jsonb,
            salary_min NUMERIC(15, 2),
            salary_max NUMERIC(15, 2),
            salary_currency VARCHAR(10) DEFAULT 'INR',
            salary_period VARCHAR(20) DEFAULT 'yearly',
            salary_raw VARCHAR(255),
            experience_min_years REAL,
            experience_max_years REAL,
            trust_score REAL DEFAULT 0.5,
            quality_score REAL DEFAULT 0.5,
            freshness_score REAL DEFAULT 1.0,
            spam_score REAL DEFAULT 0.0,
            is_active BOOLEAN DEFAULT TRUE,
            is_verified BOOLEAN DEFAULT FALSE,
            is_duplicate BOOLEAN DEFAULT FALSE,
            duplicate_of_id INT,
            lifecycle_status VARCHAR(50) DEFAULT 'discovered',
            embedding_id VARCHAR(100),
            embedding_version INT DEFAULT 0,
            qdrant_sync_pending BOOLEAN DEFAULT FALSE,
            posted_at TIMESTAMP WITH TIME ZONE,
            expires_at TIMESTAMP WITH TIME ZONE,
            discovered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            verified_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at);
        """
    )

    # Create monthly partitions for 2026/2027 to cover standard runs
    op.execute("CREATE TABLE jobs_y2026m07 PARTITION OF jobs FOR VALUES FROM ('2026-07-01 00:00:00+00') TO ('2026-08-01 00:00:00+00');")
    op.execute("CREATE TABLE jobs_y2026m08 PARTITION OF jobs FOR VALUES FROM ('2026-08-01 00:00:00+00') TO ('2026-09-01 00:00:00+00');")
    op.execute("CREATE TABLE jobs_default PARTITION OF jobs DEFAULT;")

    # Composite indexes on partitioned jobs
    op.execute("CREATE INDEX idx_job_active_quality ON jobs (is_active, quality_score);")
    op.execute("CREATE INDEX idx_job_lifecycle ON jobs (lifecycle_status, created_at);")
    op.execute("CREATE INDEX idx_job_role_seniority ON jobs (role_category, seniority, created_at);")
    op.execute("CREATE INDEX idx_job_country_city ON jobs (country, city);")
    op.execute("CREATE INDEX idx_job_external_source ON jobs (external_id, source_id);")
    op.execute("CREATE INDEX idx_job_posted_active ON jobs (posted_at, is_active);")
    op.execute("CREATE INDEX idx_job_qdrant_pending ON jobs (qdrant_sync_pending);")

    # ---------------------------------------------------------------------------
    # 4. Job Skills Table
    # ---------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE job_skills (
            id SERIAL PRIMARY KEY,
            job_id INT NOT NULL,
            job_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            skill_name VARCHAR(100) NOT NULL,
            weight REAL DEFAULT 1.0,
            is_required BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (job_id, job_created_at) REFERENCES jobs(id, created_at) ON DELETE CASCADE
        );
        """
    )
    op.execute("CREATE INDEX idx_job_skill_name ON job_skills (skill_name);")
    op.execute("CREATE INDEX idx_job_skill_job_id ON job_skills (job_id);")

    # ---------------------------------------------------------------------------
    # 5. Candidate Matches Table
    # ---------------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE candidate_matches (
            id SERIAL PRIMARY KEY,
            candidate_id INT NOT NULL,
            job_id INT NOT NULL,
            job_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            overall_score REAL NOT NULL,
            semantic_score REAL DEFAULT 0.0,
            skill_score REAL DEFAULT 0.0,
            experience_score REAL DEFAULT 0.0,
            salary_score REAL DEFAULT 0.0,
            location_score REAL DEFAULT 0.0,
            remote_preference_score REAL DEFAULT 0.0,
            company_preference_score REAL DEFAULT 0.0,
            freshness_score REAL DEFAULT 0.0,
            match_reasons JSONB DEFAULT '[]'::jsonb,
            missing_skills JSONB DEFAULT '[]'::jsonb,
            skill_gap_severity VARCHAR(20) DEFAULT 'none',
            match_explanation TEXT,
            status VARCHAR(50) DEFAULT 'new',
            is_seen BOOLEAN DEFAULT FALSE,
            is_saved BOOLEAN DEFAULT FALSE,
            is_hidden BOOLEAN DEFAULT FALSE,
            user_reaction VARCHAR(50),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id, job_created_at) REFERENCES jobs(id, created_at) ON DELETE CASCADE,
            UNIQUE (candidate_id, job_id, job_created_at)
        );
        """
    )
    op.execute("CREATE INDEX idx_match_candidate_score ON candidate_matches (candidate_id, overall_score DESC);")
    op.execute("CREATE INDEX idx_match_candidate_status ON candidate_matches (candidate_id, status);")

    # ---------------------------------------------------------------------------
    # 6. Recommendations Table
    # ---------------------------------------------------------------------------
    op.create_table(
        'recommendations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('candidate_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=True),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.REAL(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('is_seen', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_actioned', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('actioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['match_id'], ['candidate_matches.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rec_candidate_seen', 'recommendations', ['candidate_id', 'is_seen'])
    op.create_index('idx_rec_candidate_created', 'recommendations', ['candidate_id', 'created_at'])

    # ---------------------------------------------------------------------------
    # 7. Crawl History Table
    # ---------------------------------------------------------------------------
    op.create_table(
        'crawl_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=100), nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('jobs_found', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('jobs_saved', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('jobs_deduplicated', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('jobs_rejected', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_ms', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_crawl_run_source', 'crawl_history', ['run_id', 'source_name'])
    op.create_index('idx_crawl_started', 'crawl_history', ['started_at'])

    # ---------------------------------------------------------------------------
    # 8. Connector Health Table
    # ---------------------------------------------------------------------------
    op.create_table(
        'connector_health',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_connector_health_name', 'connector_health', ['source_name', 'checked_at'])

    # ---------------------------------------------------------------------------
    # 9. Job Events Table (Audit Log)
    # ---------------------------------------------------------------------------
    op.create_table(
        'job_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('correlation_id', sa.String(length=36), nullable=True),
        sa.Column('trace_id', sa.String(length=36), nullable=True),
        sa.Column('producer', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_job_event_type_created', 'job_events', ['event_type', 'created_at'])
    op.create_index('idx_job_event_correlation', 'job_events', ['correlation_id'])


def downgrade() -> None:
    op.drop_table('job_events')
    op.drop_table('connector_health')
    op.drop_table('crawl_history')
    op.drop_table('recommendations')
    op.execute("DROP TABLE candidate_matches CASCADE;")
    op.execute("DROP TABLE job_skills CASCADE;")
    op.execute("DROP TABLE jobs CASCADE;")
    op.drop_table('job_sources')
    op.drop_table('companies')
