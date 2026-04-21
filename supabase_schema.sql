-- Supabase Database Schema for TimeTravel Tasks
-- Run this in your Supabase SQL Editor
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";
-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'done')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    workspace_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);
-- Snapshots table for time-travel
CREATE TABLE snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    label TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    tasks JSONB NOT NULL, -- Store complete task list as JSON
    workspace_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000'
);
-- Current workspace state
CREATE TABLE workspace_state (
    id UUID PRIMARY KEY DEFAULT '00000000-0000-0000-0000-000000000000',
    current_snapshot_id UUID REFERENCES snapshots(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
-- Insert initial workspace state
INSERT INTO workspace_state (id) VALUES ('00000000-0000-0000-0000-000000000000');
-- Create initial snapshot
INSERT INTO snapshots (id, label, tasks, workspace_id)
VALUES (
    uuid_generate_v4(),
    'Workspace initialized',
    '[]'::jsonb,
    '00000000-0000-0000-0000-000000000000'
);
-- Update workspace to point to initial snapshot
UPDATE workspace_state
SET current_snapshot_id = (SELECT id FROM snapshots WHERE label = 'Workspace initialized' LIMIT 1);
-- Enable Row Level Security (RLS)
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_state ENABLE ROW LEVEL SECURITY;
-- Create policies (adjust based on your auth needs)
-- For now, allow all operations (you can restrict later)
CREATE POLICY \"Allow all operations on tasks\" ON tasks FOR ALL USING (true);
CREATE POLICY \"Allow all operations on snapshots\" ON snapshots FOR ALL USING (true);
CREATE POLICY \"Allow all operations on workspace_state\" ON workspace_state FOR ALL USING (true);
-- Create indexes for better performance
CREATE INDEX idx_tasks_workspace_id ON tasks(workspace_id);
CREATE INDEX idx_snapshots_workspace_id ON snapshots(workspace_id);
CREATE INDEX idx_snapshots_created_at ON snapshots(created_at);
