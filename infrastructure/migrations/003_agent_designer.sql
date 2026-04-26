-- migrations/003_agent_designer.sql

CREATE TABLE IF NOT EXISTS agency_repos (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    path TEXT NOT NULL,
    stack VARCHAR(50) NOT NULL,
    repo_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_designer_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) UNIQUE NOT NULL,
    chat_id VARCHAR(50),
    user_id VARCHAR(50),
    source VARCHAR(20),
    repo_url TEXT NOT NULL,
    stack VARCHAR(50),
    state VARCHAR(20) NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_active
ON agent_designer_sessions (chat_id, user_id, state)
WHERE state NOT IN ('COMPLETE', 'ERROR', 'CANCELLED');

CREATE INDEX IF NOT EXISTS idx_sessions_user
ON agent_designer_sessions (user_id, state)
WHERE state NOT IN ('COMPLETE', 'ERROR', 'CANCELLED');

-- Seed existing repos
INSERT INTO agency_repos (name, path, stack, repo_url) VALUES
('falara', '/opt/agency/repos/falara', 'fastapi', 'https://github.com/borisdeluxe/falara'),
('falara-frontend', '/opt/agency/repos/falara-frontend', 'react-vite', 'https://github.com/borisdeluxe/falara-frontend')
ON CONFLICT (name) DO NOTHING;
