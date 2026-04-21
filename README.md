# TimeTravel Tasks

A simple task manager with undo/redo features. Create tasks, organize them in hierarchies, and go back in time to fix mistakes.

## Quick Start

1. Install Python 3.10 or higher
2. Install dependencies: `pip install flask flask-cors supabase`
3. Set up Supabase (optional for data persistence)
4. Run: `python app.py`
5. Open http://127.0.0.1:5000

## How to Use

- **Create Tasks**: Enter a title, choose a parent if needed, pick status, click "Add Task"
- **Edit Tasks**: Click a task, change details in the right panel, save
- **Delete Tasks**: Click delete (removes task and all subtasks)
- **Undo/Redo**: Use buttons or slider to go back/forward in history

## Features

- Hierarchical tasks (parent-child)
- Undo/Redo with full history
- Time travel slider
- Simple web interface

## How It Works

### Main Idea

This app lets you manage tasks with the ability to undo changes, like time travel in a document editor.

### Key Concepts

- **Tasks**: Each task has a title, status (todo/in progress/done), and can have a parent task for organization.
- **History**: Every change saves a snapshot of all tasks. You can jump back to any previous state.
- **Undo/Redo**: Go back or forward one step at a time.
- **Cascade Delete**: Deleting a task removes it and all its subtasks.

### How Time Travel Works

1. When you make a change, the app saves the current state.
2. History keeps all past states.
3. You can switch to any saved state using the slider or buttons.

### Tech Stuff

- Built with Flask (Python web framework)
- Uses Supabase for data storage (optional)
- Falls back to local JSON file if no Supabase
- Web interface with HTML/CSS/JS

## Deployment

### Quick Deploy to Vercel

1. Sign up for free accounts: Vercel and Supabase
2. Create a Supabase project and run the schema from `supabase_schema.sql`
3. Copy your Supabase URL and API key
4. Push code to GitHub
5. Import project in Vercel from GitHub
6. Set environment variables in Vercel: SUPABASE_URL and SUPABASE_ANON_KEY
7. Deploy!

### Local Setup

- Install Python and dependencies
- Set SUPABASE_URL and SUPABASE_ANON_KEY as environment variables
- Run `python app.py`

### Notes

- Free tiers available for both services
- Data persists with Supabase
- Without Supabase, data is local only

## Project Files

- `app.py`: Main app with Supabase integration and production file system fixes
- `requirements.txt`: Dependencies
- `templates/index.html`: Web page
- `static/`: CSS and JS files
- `data/`: Local data storage (development only)
- `.env.example`: Environment configuration template

## Production Notes

- **File System**: Automatically uses `/tmp` in serverless environments (Vercel, AWS Lambda)
- **Supabase Required**: Production deployments should use Supabase for data persistence
- **Environment Variables**: Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` for production
