-- Agency Database Schema
-- Version: 001
-- Date: 2026-04-24

-- Live Snapshot (Singleton)
CREATE TABLE agency_live_snapshot (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data JSONB NOT NULL
);

-- Events (Append-only log)
CREATE TABLE agency_events (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,  -- agent_started, agent_finished, gate_passed, gate_failed, error, budget_warning
    feature_id TEXT,
    agent_id TEXT,
    data JSONB
);
CREATE INDEX idx_events_created ON agency_events (created_at DESC);
CREATE INDEX idx_events_feature ON agency_events (feature_id) WHERE feature_id IS NOT NULL;

-- Hourly Metrics (Aggregated)
CREATE TABLE agency_metrics_hourly (
    hour TIMESTAMPTZ PRIMARY KEY,
    features_started INT DEFAULT 0,
    features_completed INT DEFAULT 0,
    features_failed INT DEFAULT 0,
    total_cost_eur NUMERIC(10,4) DEFAULT 0,
    total_tokens_in BIGINT DEFAULT 0,
    total_tokens_out BIGINT DEFAULT 0,
    avg_feature_duration_min NUMERIC(10,2)
);

-- Task Queue (Persistent)
CREATE TABLE agency_tasks (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feature_id TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,  -- github_issue, cli
    source_ref TEXT,       -- issue URL or CLI command
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, in_progress, completed, failed, cancelled
    priority INT DEFAULT 0,
    data JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cost_eur NUMERIC(10,4) DEFAULT 0,
    current_agent TEXT,
    error TEXT
);
CREATE INDEX idx_tasks_status ON agency_tasks (status);

-- Pipeline Metrics (Per Agent Run)
CREATE TABLE pipeline_metrics (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    feature_id TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    model TEXT,
    tokens_in BIGINT,
    tokens_out BIGINT,
    cache_read BIGINT DEFAULT 0,
    cost_eur NUMERIC(10,4),
    duration_ms INT,
    exit_status TEXT,
    gate_result TEXT,
    diff_loc_added INT,
    diff_files_changed INT,
    tests_added INT,
    coverage_delta NUMERIC(5,2)
);
CREATE INDEX idx_metrics_feature ON pipeline_metrics (feature_id);
CREATE INDEX idx_metrics_created ON pipeline_metrics (created_at DESC);
