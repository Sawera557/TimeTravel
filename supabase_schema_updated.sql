-- Supabase Database Schema for TimeTravel Tasks
-- Run this in your Supabase SQL Editor
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'done')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    workspace_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);

-- Snapshots table for time-travel
CREATE TABLE IF NOT EXISTS snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    label TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    tasks JSONB NOT NULL,
    workspace_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);

-- Current workspace state
CREATE TABLE IF NOT EXISTS workspace_state (
    id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000000',
    current_snapshot_id UUID REFERENCES snapshots(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert initial workspace state with conflict handling
INSERT INTO workspace_state (id) VALUES ('00000000-0000-0000-0000-000000000000')
ON CONFLICT (id) DO NOTHING;

-- Create initial snapshot with fixed UUID
INSERT INTO snapshots (id, label, tasks, workspace_id)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Workspace initialized',
    '[]'::jsonb,
    '00000000-0000-0000-0000-000000000000'
)
ON CONFLICT (id) DO NOTHING;

-- Update workspace to point to initial snapshot
UPDATE workspace_state
SET current_snapshot_id = '11111111-1111-1111-1111-111111111111'
WHERE id = '00000000-0000-0000-0000-000000000000' AND current_snapshot_id IS NULL;

-- Enable Row Level Security (RLS)
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_state ENABLE ROW LEVEL SECURITY;

-- Drop existing policies to avoid conflicts
DROP POLICY IF EXISTS "Allow all operations on tasks" ON tasks;
DROP POLICY IF EXISTS "Allow all operations on snapshots" ON snapshots;
DROP POLICY IF EXISTS "Allow all operations on workspace_state" ON workspace_state;

-- Create policies (allow all operations for development - restrict in production)
CREATE POLICY "Allow all operations on tasks" ON tasks FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on snapshots" ON snapshots FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on workspace_state" ON workspace_state FOR ALL USING (true) WITH CHECK (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_tasks_workspace_id ON tasks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_workspace_id ON snapshots(workspace_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created_at ON snapshots(created_at);

