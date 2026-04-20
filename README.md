# Chronicle Tasks
A professional task manager with time-travel functionality. Supports hierarchical tasks, undo/redo, and snapshot-based history navigation.
## Quick Start
### Prerequisites
- Python 3.10+
- pip
### Installation & Run
`ash
# Install dependencies
pip install flask flask-cors
# Run the app
python app.py
`
Open [http://127.0.0.1:5000](http://127.0.0.1:5000)
## Features
- ✅ Create hierarchical tasks (parent-child relationships)
- ✅ Edit tasks inline (title, status, parent)
- ✅ Delete tasks with cascade (removes all descendants)
- ✅ Undo/Redo with full state restoration
- ✅ Time-travel slider to jump between snapshots
- ✅ History branching when editing from past states
- ✅ Cycle prevention (no circular dependencies)
- ✅ Real-time UI updates
## How to Use
### Create Tasks
1. Enter title in left panel
2. Select parent (optional)
3. Choose status (todo/in_progress/done)
4. Click "Add Task"
### Edit Tasks
1. Click any task card in center panel
2. Use right inspector to modify
3. Click "Save Changes"
### Time Travel
- **Undo/Redo**: Click buttons for step-by-step navigation
- **Slider**: Drag to jump to any historical state
- **History List**: Click any snapshot to jump directly
### Delete Tasks
- Select task → Click "Delete Task"
- Automatically removes all child tasks (cascade delete)
## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | / | Web interface |
| GET | /health | Health check |
| GET | /api/tasks | Get all tasks |
| POST | /api/tasks | Create task |
| PATCH | /api/tasks/<id> | Update task |
| DELETE | /api/tasks/<id> | Delete task + descendants |
| GET | /api/history | Get snapshot history |
| POST | /api/history/travel | Jump to snapshot |
| POST | /api/undo | Undo one step |
| POST | /api/redo | Redo one step |
| POST | /api/init | Reset workspace |
## Project Structure
`
FlaskProject/
├── app.py                 # Flask backend + business logic
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── DEPLOYMENT.md         # Vercel deployment guide
├── ARCHITECTURE.md       # Technical concepts
├── templates/
│   └── index.html        # Single-page app template
├── static/
│   ├── css/
│   │   └── app.css       # Professional styling
│   └── js/
│       └── app.js        # Frontend state management
└── data/
    └── task_state.json   # JSON persistence
`
## Core Concepts
### State Management
- **Snapshot-based**: Every change creates a complete state snapshot
- **Immutable history**: Past snapshots never modified
- **Current index**: Points to active snapshot in history array
### Dependency Strategy
- **Cascade delete**: Parent deletion removes all descendants
- **Cycle prevention**: Validates parent relationships to prevent loops
- **Stable IDs**: Task IDs remain consistent across undo/redo
### Time Travel
- **Undo/Redo**: Navigate history step-by-step
- **Branching**: Editing from past creates new timeline
- **Restoration**: Complete state restoration maintains relationships
## Testing
Run comprehensive test suite:
`ash
python test_e2e.py
`
Tests cover: CRUD operations, undo/redo, time travel, cascade delete, cycle prevention, validation.
## Troubleshooting
### Module not found
`ash
pip install flask flask-cors
`
### Data stuck
Reset workspace:
`ash
curl -X POST http://localhost:5000/api/init
`
### Port in use
Kill existing process:
`ash
# Windows
taskkill /F /IM python.exe
# macOS/Linux
pkill -f "python app.py"
`
## Technical Details
See [ARCHITECTURE.md](ARCHITECTURE.md) for:
- State model explanation
- File architecture
- API design decisions
- Performance considerations
## Deployment
See [DEPLOYMENT.md](DEPLOYMENT.md) for Vercel deployment instructions.
