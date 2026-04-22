# TimeTravel Tasks - Flask + Supabase

A real-time task management application with undo/redo and time-travel capabilities powered by Flask and Supabase PostgreSQL.

## 🚀 Quick Start

### 1. Database Setup (Most Important!)

Your application needs Supabase database tables. **This is likely why you're seeing errors.**

**3-minute fix:**

#### Step 1: Run Setup Checker
```powershell
python quick_setup.py
```

#### Step 2: Create Database Schema
1. Go to: https://app.supabase.com/project/txsrejfrqlhrheqcsmzp
2. Click **SQL Editor** → **New Query**
3. Copy contents of: `supabase_schema_updated.sql`
4. Click **Run**

#### Step 3: Restart App
```powershell
python app.py
```

### 2. Environment Configuration

Create `.env` file in project root:
```
SUPABASE_URL=https://txsrejfrqlhrheqcsmzp.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
```

Get these values from Supabase:
- Dashboard → Project Settings → API → Copy the values

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Run Application
```powershell
python app.py
```

Visit: http://localhost:5000

## 📁 File Structure

```
FlaskProject/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── supabase_schema.sql             # Original database schema
├── supabase_schema_updated.sql     # Improved schema (use this one)
├── .env                            # Environment variables (create this!)
├── README.md                       # This file
├── quick_setup.py                  # Quick setup checker
├── setup_supabase.py               # Python setup verification
├── static/
│   ├── css/
│   │   └── app.css
│   └── js/
│       └── app.js
├── templates/
│   └── index.html
└── data/
    └── task_state.json            # Local fallback storage
```

## 🔧 Features

### Task Management
- ✅ Create tasks with hierarchical structure
- ✅ Update task status (todo → in_progress → done)
- ✅ Delete tasks (cascades to children)
- ✅ Nested/subtask support

### Time Travel
- ⏪ Undo/Redo - Go back/forward in history
- 🕐 Jump to any snapshot
- 📸 View history of all changes
- 🌳 Non-destructive branching

### Data Persistence
- 🗄️ **Primary**: Supabase PostgreSQL Database
- 📄 **Fallback**: Local JSON file (automatic)
- 🔄 Automatic failover if Supabase is unavailable

## 🔌 API Endpoints

### Tasks
```
GET    /api/tasks              # List all tasks
POST   /api/tasks              # Create new task
PATCH  /api/tasks/<id>         # Update task
DELETE /api/tasks/<id>         # Delete task
```

### History
```
GET    /api/history            # Get all snapshots
POST   /api/history/travel     # Jump to snapshot index
POST   /api/undo               # Undo last change
POST   /api/redo               # Redo undone change
```

### System
```
GET    /health                 # Health status
POST   /api/init              # Reset workspace
GET    /api/diagnostic        # Detailed diagnostics
```

## 🐛 Troubleshooting

### Error: "Could not find the table 'public.workspace_state'"

This means the database schema hasn't been created yet.

**Fix:**
1. Run `python quick_setup.py` to see status
2. Go to Supabase SQL Editor
3. Run the schema from `supabase_schema_updated.sql`
4. Restart Flask app

### Error: "SUPABASE_URL not found"

`.env` file missing or not in the right place.

**Fix:**
1. Create `.env` in project root (same folder as `app.py`)
2. Add the credentials from Supabase dashboard
3. Restart Flask app

### Application running but using "file" storage instead of "supabase"

Supabase connection issue - check logs.

**Fix:**
1. Visit `http://localhost:5000/api/diagnostic` to see issue
2. Verify `.env` has correct credentials
3. Check Supabase project is not paused
4. Verify internet connection
5. See Flask console for error details

## 📊 Database Schema

### Tasks Table
```sql
- id (UUID) - Primary key
- title (TEXT) - Task name
- parent_id (UUID) - For hierarchical structure
- status (TEXT) - 'todo' | 'in_progress' | 'done'
- created_at (TIMESTAMPTZ) - Creation time
- updated_at (TIMESTAMPTZ) - Last update
- workspace_id (UUID) - Workspace identifier
```

### Snapshots Table
```sql
- id (UUID) - Snapshot identifier
- label (TEXT) - Human readable label
- created_at (TIMESTAMPTZ) - When snapshot was taken
- tasks (JSONB) - Serialized task list
- workspace_id (UUID) - Workspace identifier
```

### Workspace State Table
```sql
- id (UUID) - Workspace identifier
- current_snapshot_id (UUID) - Points to active snapshot
- created_at (TIMESTAMPTZ) - Creation time
- updated_at (TIMESTAMPTZ) - Last update
```

## 🏗️ Architecture

```
┌─────────────────────────┐
│   Browser / Frontend    │
│   (HTML + JS/CSS)       │
└──────────────┬──────────┘
               │
               ↓ HTTP Requests
┌─────────────────────────┐
│  Flask Web Server       │
│  - Routing              │
│  - CORS Headers         │
│  - Static Files         │
└──────────────┬──────────┘
               │
               ↓
┌─────────────────────────┐
│  TaskManager            │
│  - Business Logic       │
│  - Validation           │
│  - Undo/Redo Logic      │
└──────────────┬──────────┘
               │
               ↓
┌─────────────────────────┐
│  SupabaseStore          │
│  - Persistence Layer    │
│  - Try Supabase         │
│  - Fallback to File     │
└──────────────┬──────────┘
               │
        ┌──────┴──────┐
        ↓             ↓
    ┌───────┐    ┌───────────┐
    │ File  │    │ Supabase  │
    │ JSON  │    │ Postgre   │
    │       │    │ SQL       │
    └───────┘    └───────────┘
```

## 🔐 Security Notes

### Development
- Row Level Security (RLS) enabled
- Policies allow all operations (for testing)
- Using anon (public) key

### Production Considerations
- ⚠️ Update RLS policies with proper restrictions
- ⚠️ Set up Supabase Auth for user authentication
- ⚠️ Use service role key only on backend
- ⚠️ Enable database backups
- ⚠️ Set up rate limiting
- ⚠️ Configure CORS for specific domains
- ⚠️ Add audit logging

## 📝 How It Works

### Creating a Task
1. User submits form → Flask `/api/tasks` POST
2. TaskManager validates input
3. Task created in memory
4. **Snapshot saved** to Supabase (with label)
5. All tasks saved to Supabase
6. Response sent to frontend
7. UI updates with new task

### Undo Operation
1. User clicks undo → Flask `/api/undo` POST
2. TaskManager gets current state index
3. Decrements index by 1
4. Loads snapshot at that index
5. Restores tasks from that snapshot
6. Updates workspace_state pointer in Supabase
7. Response with new state
8. UI updates with previous state

### Time Travel
1. User selects historical snapshot
2. Flask `/api/history/travel` POST with index
3. TaskManager validates index is in range
4. Loads snapshot at that index
5. Sets current_index to that point
6. Any new action branches from here (truncates future)
7. UI updates with that historical state

## 🚀 Running for Development

```powershell
# Terminal 1: Run Flask app
python app.py

# Terminal 2: (Optional) Monitor logs
# Or just watch the Flask terminal output

# Browser: Visit app
http://localhost:5000
```

### Development Features
- Hot reload disabled (for stability)
- Debug logging enabled
- Full error stack traces
- File storage fallback ready

## 📦 Dependencies

```
flask              # Web framework
flask-cors         # Cross-origin requests
supabase           # Database client
python-dotenv      # Environment variables
```

Install with:
```powershell
pip install -r requirements.txt
```

## 🤝 Support

If something isn't working:

1. **Check Status**: `python quick_setup.py`
2. **View Diagnostics**: `http://localhost:5000/api/diagnostic`
3. **Check Health**: `http://localhost:5000/health`
4. **Review Logs**: Watch Flask console output

## 📄 License

Open source project for learning and development.

---

**Ready to get started?** 
1. Run: `python quick_setup.py`
2. Follow the instructions it provides
3. Visit: `http://localhost:5000`

Happy task managing! 🎉
