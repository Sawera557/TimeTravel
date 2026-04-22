import os
import logging
from supabase import create_client, Client
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file in development
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✓ Loaded environment variables from .env file")
except ImportError:
    logger.warning("⚠ python-dotenv not installed, using system environment variables only")

app = Flask(__name__, static_folder='static', static_url_path='/static')
CORS(app)

# Configure caching for static files
@app.after_request
def add_cache_headers(response):
    """Add cache headers for static files"""
    if response.status_code == 200:
        # This app serves unhashed assets, so force revalidation to avoid stale JS/CSS in production.
        if request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, no-cache, max-age=0, must-revalidate'
        elif request.path == '/' or request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
    return response

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')

# Initialize Supabase client
supabase: Client | None = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        logger.info("✓ Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"✗ Failed to initialize Supabase client: {e}")
        supabase = None
else:
    logger.warning("⚠ Supabase credentials not found. Using local file storage only.")
# Fallback to file storage for local development
# In production/serverless environments, use /tmp directory
is_production = os.getenv('VERCEL') or os.getenv('AWS_LAMBDA_FUNCTION_NAME') or os.getenv('LAMBDA_TASK_ROOT')
if is_production:
    STORE_PATH = Path('/tmp/task_state.json')
    logger.info("✓ Using /tmp for file storage in production environment")
else:
    STORE_PATH = Path(__file__).with_name('data').joinpath('task_state.json')
    logger.info("✓ Using local data directory for file storage")
LOCK = RLock()
def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
def clone_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return deepcopy(tasks)
class SupabaseStore:
    def __init__(self):
        self.workspace_id = '00000000-0000-0000-0000-000000000000'  # Default workspace
    def _default_state(self) -> dict[str, Any]:
        empty_snapshot = {
            'id': str(uuid4()),
            'label': 'Workspace initialized',
            'created_at': utc_now(),
            'tasks': [],
        }
        return {
            'tasks': [],
            'history': [empty_snapshot],
            'current_index': 0,
        }
    def load(self) -> dict[str, Any]:
        '''Load current workspace state from Supabase or fallback to file'''
        if supabase:
            try:
                # Get current workspace state
                workspace_response = supabase.table('workspace_state').select('*').eq('id', self.workspace_id).execute()
                if not workspace_response.data:
                    logger.info(f"Workspace {self.workspace_id} not found in Supabase, initializing...")
                    return self._initialize_supabase()
                workspace = workspace_response.data[0]
                current_snapshot_id = workspace.get('current_snapshot_id')
                if not current_snapshot_id:
                    logger.warning(f"No current snapshot for workspace {self.workspace_id}, reinitializing...")
                    return self._initialize_supabase()
                # Get current snapshot
                snapshot_response = supabase.table('snapshots').select('*').eq('id', current_snapshot_id).execute()
                if not snapshot_response.data:
                    logger.error(f"Snapshot {current_snapshot_id} not found in Supabase")
                    return self._initialize_supabase()
                current_snapshot = snapshot_response.data[0]
                # Get all snapshots for history
                history_response = supabase.table('snapshots').select('*').eq('workspace_id', self.workspace_id).order('created_at').execute()
                history = []
                current_index = 0
                for i, snap in enumerate(history_response.data):
                    # Properly deserialize tasks from JSONB
                    tasks_data = snap['tasks']
                    if isinstance(tasks_data, str):
                        tasks_data = json.loads(tasks_data)
                    history.append({
                        'id': snap['id'],
                        'label': snap['label'],
                        'created_at': snap['created_at'],
                        'tasks': tasks_data
                    })
                    if snap['id'] == current_snapshot_id:
                        current_index = i
                # Get current tasks from snapshot
                tasks = current_snapshot['tasks'] if isinstance(current_snapshot['tasks'], list) else json.loads(current_snapshot['tasks'])
                logger.info(f"✓ Loaded {len(tasks)} tasks from Supabase (snapshot {current_snapshot_id[:8]}...)")
                return {
                    'tasks': tasks,
                    'history': history,
                    'current_index': current_index
                }
            except Exception as e:
                logger.error(f'Error loading from Supabase: {e}', exc_info=True)
                logger.info("Falling back to file storage")
                return self._load_from_file()
        else:
            logger.debug("Supabase not available, using file storage")
            return self._load_from_file()
    def _initialize_supabase(self) -> dict[str, Any]:
        '''Initialize Supabase with default state'''
        try:
            # Use fixed UUID for initial snapshot (same as SQL schema)
            initial_snapshot_id = '11111111-1111-1111-1111-111111111111'
            
            # Check if initial snapshot already exists (created by SQL schema)
            snapshot_check = supabase.table('snapshots').select('*').eq('id', initial_snapshot_id).execute()
            
            if not snapshot_check.data:
                # Create initial snapshot if it doesn't exist
                initial_snapshot = {
                    'id': initial_snapshot_id,
                    'label': 'Workspace initialized',
                    'created_at': utc_now(),
                    'tasks': [],
                    'workspace_id': self.workspace_id
                }
                supabase.table('snapshots').insert({
                    'id': initial_snapshot['id'],
                    'label': initial_snapshot['label'],
                    'created_at': initial_snapshot['created_at'],
                    'tasks': json.dumps(initial_snapshot['tasks']),
                    'workspace_id': self.workspace_id
                }).execute()
            
            # Update workspace state to point to initial snapshot
            supabase.table('workspace_state').update({
                'current_snapshot_id': initial_snapshot_id,
                'updated_at': utc_now()
            }).eq('id', self.workspace_id).execute()
            
            logger.info(f"✓ Supabase workspace {self.workspace_id} initialized")
            return {
                'tasks': [],
                'history': [{
                    'id': initial_snapshot_id,
                    'label': 'Workspace initialized',
                    'created_at': utc_now(),
                    'tasks': []
                }],
                'current_index': 0
            }
        except Exception as e:
            logger.error(f'Error initializing Supabase: {e}', exc_info=True)
            return self._default_state()
    def _load_from_file(self) -> dict[str, Any]:
        '''Fallback file-based loading'''
        with LOCK:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not STORE_PATH.exists():
                state = self._default_state()
                STORE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
                return state
            return json.loads(STORE_PATH.read_text(encoding='utf-8'))
    def save(self, state: dict[str, Any]) -> None:
        '''Save current state to Supabase or fallback to file'''
        if supabase:
            try:
                # Update current snapshot pointer
                if state['history'] and state['current_index'] < len(state['history']):
                    current_snapshot = state['history'][state['current_index']]
                    supabase.table('workspace_state').update({
                        'current_snapshot_id': current_snapshot['id'],
                        'updated_at': utc_now()
                    }).eq('id', self.workspace_id).execute()
                    logger.debug(f"Updated workspace state to snapshot {current_snapshot['id']}")
                    logger.debug(f"Saved snapshot with {len(state['tasks'])} tasks")
            except Exception as e:
                logger.error(f'Error saving to Supabase: {e}', exc_info=True)
                logger.info("Falling back to file storage")
                self._save_to_file(state)
        else:
            self._save_to_file(state)
    def _save_to_file(self, state: dict[str, Any]) -> None:
        '''Fallback file-based saving'''
        with LOCK:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STORE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')
    def save_snapshot(self, state: dict[str, Any], label: str) -> dict[str, Any]:
        '''Create and save a new snapshot'''
        # Truncate future history (for branching)
        history = state['history'][: state['current_index'] + 1]
        snapshot = {
            'id': str(uuid4()),
            'label': label,
            'created_at': utc_now(),
            'tasks': deepcopy(state['tasks']),
            'workspace_id': self.workspace_id
        }
        if supabase:
            try:
                # Save to Supabase with proper JSON serialization
                snapshot_data = {
                    'id': snapshot['id'],
                    'label': snapshot['label'],
                    'created_at': snapshot['created_at'],
                    'tasks': json.dumps(snapshot['tasks']) if snapshot['tasks'] else '[]',
                    'workspace_id': self.workspace_id
                }
                supabase.table('snapshots').insert(snapshot_data).execute()
                logger.info(f"✓ Snapshot created: {label} with {len(snapshot['tasks'])} tasks")
                
                # Update workspace pointer
                supabase.table('workspace_state').update({
                    'current_snapshot_id': snapshot['id'],
                    'updated_at': utc_now()
                }).eq('id', self.workspace_id).execute()
                logger.debug(f"✓ Workspace state updated to snapshot {snapshot['id']}")
            except Exception as e:
                logger.error(f'Error saving snapshot to Supabase: {e}', exc_info=True)
        # Update local history
        history.append(snapshot)
        state['history'] = history
        state['current_index'] = len(history) - 1
        return snapshot
    def reset(self) -> dict[str, Any]:
        '''Reset workspace to initial state'''
        if supabase:
            try:
                # Clear all data for this workspace
                supabase.table('tasks').delete().eq('workspace_id', self.workspace_id).execute()
                supabase.table('snapshots').delete().eq('workspace_id', self.workspace_id).execute()
                logger.info(f"✓ Workspace {self.workspace_id} reset in Supabase")
                # Re-initialize
                return self._initialize_supabase()
            except Exception as e:
                logger.error(f'Error resetting Supabase: {e}', exc_info=True)
        # Fallback to file reset
        state = self._default_state()
        self._save_to_file(state)
        logger.info("Workspace reset to file storage")
        return state
# Initialize store
store = SupabaseStore()
class TaskManager:
    @staticmethod
    def get_state() -> dict[str, Any]:
        return store.load()
    @staticmethod
    def get_all_tasks() -> list[dict[str, Any]]:
        return TaskManager.get_state()['tasks']
    @staticmethod
    def _build_history_payload(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                'id': item['id'],
                'label': item['label'],
                'created_at': item['created_at'],
                'task_count': len(item['tasks']) if isinstance(item['tasks'], list) else len(json.loads(item['tasks'])),
            }
            for item in history
        ]
    @staticmethod
    def build_workspace_payload(state: dict[str, Any]) -> dict[str, Any]:
        tasks = sorted(clone_tasks(state['tasks']), key=lambda item: item['created_at'])
        history = TaskManager._build_history_payload(state['history'])
        current_index = state['current_index']
        return {
            'tasks': tasks,
            'history': history,
            'current_index': current_index,
            'latest_index': max(len(history) - 1, 0),
            'total': len(history),
            'strategy': 'cascade_delete',
        }
    @staticmethod
    def get_workspace() -> dict[str, Any]:
        return TaskManager.build_workspace_payload(TaskManager.get_state())
    @staticmethod
    def _save_snapshot(state: dict[str, Any], label: str) -> dict[str, Any]:
        return store.save_snapshot(state, label)
    @staticmethod
    def _find_task(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
        return next((task for task in tasks if task['id'] == task_id), None)
    @staticmethod
    def _assert_parent_is_valid(
        tasks: list[dict[str, Any]],
        task_id: str | None,
        parent_id: str | None,
    ) -> None:
        if parent_id is None:
            return
        parent = TaskManager._find_task(tasks, parent_id)
        if parent is None:
            raise ValueError('Selected parent task does not exist.')
        if task_id is not None and parent_id == task_id:
            raise ValueError('A task cannot be its own parent.')
        ancestor_id = parent.get('parent_id')
        while ancestor_id:
            if ancestor_id == task_id:
                raise ValueError('This change would create a parent-child cycle.')
            ancestor = TaskManager._find_task(tasks, ancestor_id)
            ancestor_id = ancestor.get('parent_id') if ancestor else None
    @staticmethod
    def create_task(title: str, parent_id: str | None, status: str) -> dict[str, Any]:
        state = TaskManager.get_state()
        tasks = state['tasks']
        TaskManager._assert_parent_is_valid(tasks, None, parent_id)
        task = {
            'id': str(uuid4()),
            'title': title.strip(),
            'parent_id': parent_id,
            'status': status,
            'created_at': utc_now(),
            'updated_at': utc_now(),
        }
        tasks.append(task)
        TaskManager._save_snapshot(state, f"Created '{task['title']}'")
        store.save(state)
        return task
    @staticmethod
    def update_task(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        state = TaskManager.get_state()
        tasks = state['tasks']
        task = TaskManager._find_task(tasks, task_id)
        if task is None:
            raise LookupError('Task not found.')
        title = str(payload.get('title', task['title'])).strip()
        status = payload.get('status', task['status'])
        parent_id = payload.get('parent_id', task['parent_id'])
        if parent_id == '':
            parent_id = None
        if not title:
            raise ValueError('Title is required.')
        if status not in {'todo', 'in_progress', 'done'}:
            raise ValueError('Invalid status.')
        TaskManager._assert_parent_is_valid(tasks, task_id, parent_id)
        task['title'] = title
        task['status'] = status
        task['parent_id'] = parent_id
        task['updated_at'] = utc_now()
        TaskManager._save_snapshot(state, f"Updated '{task['title']}'")
        store.save(state)
        return task
    @staticmethod
    def _get_descendant_ids(task_id: str, tasks: list[dict[str, Any]]) -> list[str]:
        descendants = [task_id]
        children = [task for task in tasks if task.get('parent_id') == task_id]
        for child in children:
            descendants.extend(TaskManager._get_descendant_ids(child['id'], tasks))
        return descendants
    @staticmethod
    def delete_task(task_id: str) -> dict[str, Any]:
        state = TaskManager.get_state()
        tasks = state['tasks']
        task = TaskManager._find_task(tasks, task_id)
        if task is None:
            raise LookupError('Task not found.')
        deleted_ids = set(TaskManager._get_descendant_ids(task_id, tasks))
        state['tasks'] = [item for item in tasks if item['id'] not in deleted_ids]
        TaskManager._save_snapshot(state, f"Deleted '{task['title']}' and descendants")
        store.save(state)
        return {
            'deleted_count': len(deleted_ids),
            'deleted_ids': list(deleted_ids),
            'strategy': 'cascade_delete',
        }
    @staticmethod
    def get_history() -> list[dict[str, Any]]:
        history = TaskManager.get_state()['history']
        return TaskManager._build_history_payload(history)
    @staticmethod
    def get_current_index() -> int:
        return TaskManager.get_state()['current_index']
    @staticmethod
    def travel_to_state(index: int) -> dict[str, Any] | None:
        state = TaskManager.get_state()
        history = state['history']
        
        # Validate index bounds
        if not history:
            logger.warning("No history available")
            return None
        
        if index < 0 or index >= len(history):
            logger.warning(f"Invalid index {index}, valid range is 0-{len(history)-1}")
            return None
        
        snapshot = history[index]
        
        # Safely deserialize tasks
        tasks = snapshot.get('tasks', [])
        if isinstance(tasks, str):
            try:
                tasks = json.loads(tasks)
            except (json.JSONDecodeError, TypeError):
                logger.error(f"Failed to deserialize tasks from snapshot {snapshot['id']}")
                tasks = []
        elif tasks is None:
            tasks = []
        
        # Ensure tasks is a list
        if not isinstance(tasks, list):
            logger.warning(f"Tasks is not a list: {type(tasks)}")
            tasks = []
        
        state['current_index'] = index
        state['tasks'] = clone_tasks(tasks)
        store.save(state)
        
        return {
            'index': index,
            'snapshot': {
                'id': snapshot['id'],
                'label': snapshot['label'],
                'created_at': snapshot['created_at'],
                'task_count': len(state['tasks']),
            },
            'tasks': state['tasks'],
        }
    @staticmethod
    def undo() -> dict[str, Any] | None:
        return TaskManager.travel_to_state(TaskManager.get_current_index() - 1)
    @staticmethod
    def redo() -> dict[str, Any] | None:
        return TaskManager.travel_to_state(TaskManager.get_current_index() + 1)
    @staticmethod
    def initialize() -> dict[str, Any]:
        return store.reset()
# Flask routes (same as before)
@app.route('/', methods=['GET'])
def index() -> str:
    return render_template('index.html')
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    tasks = sorted(TaskManager.get_all_tasks(), key=lambda item: item['created_at'])
    return jsonify({'tasks': tasks, 'strategy': 'cascade_delete'}), 200
@app.route('/api/workspace', methods=['GET'])
def get_workspace():
    return jsonify(TaskManager.get_workspace()), 200
@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json(silent=True) or {}
        title = str(data.get('title', '')).strip()
        parent_id = data.get('parent_id') or None
        status = data.get('status', 'todo')
        if not title:
            logger.warning("Task creation attempt with empty title")
            return jsonify({'error': 'Title is required.'}), 400
        if status not in {'todo', 'in_progress', 'done'}:
            logger.warning(f"Task creation attempt with invalid status: {status}")
            return jsonify({'error': 'Invalid status.'}), 400
        task = TaskManager.create_task(title, parent_id, status)
        logger.info(f"✓ Task created: {task['id']}")
        return jsonify({'task': task, 'workspace': TaskManager.get_workspace()}), 201
    except ValueError as exc:
        logger.warning(f"Task creation validation error: {exc}")
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        logger.error(f"Task creation error: {exc}", exc_info=True)
        return jsonify({'error': str(exc)}), 500
@app.route('/api/tasks/<task_id>', methods=['PATCH'])
def update_task(task_id: str):
    try:
        data = request.get_json(silent=True) or {}
        task = TaskManager.update_task(task_id, data)
        return jsonify({'task': task, 'workspace': TaskManager.get_workspace()}), 200
    except LookupError as exc:
        return jsonify({'error': str(exc)}), 404
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id: str):
    try:
        result = TaskManager.delete_task(task_id)
        return jsonify({**result, 'workspace': TaskManager.get_workspace()}), 200
    except LookupError as exc:
        return jsonify({'error': str(exc)}), 404
    except Exception as exc:
        return jsonify({'error': str(exc)}), 500
@app.route('/api/history', methods=['GET'])
def get_history():
    history = TaskManager.get_history()
    return jsonify(
        {
            'history': history,
            'current_index': TaskManager.get_current_index(),
            'latest_index': max(len(history) - 1, 0),
            'total': len(history),
        }
    ), 200
@app.route('/api/history/travel', methods=['POST'])
def travel_to_state():
    try:
        data = request.get_json(silent=True) or {}
        if 'index' not in data:
            return jsonify({'error': 'Index is required.'}), 400
        
        try:
            index = int(data['index'])
        except (ValueError, TypeError):
            return jsonify({'error': 'Index must be a valid number.'}), 400
        
        state = TaskManager.travel_to_state(index)
        if state is None:
            history = TaskManager.get_history()
            total = len(history)
            return jsonify({
                'error': f'Invalid index {index}. Valid range is 0-{max(0, total-1)}.',
                'current_index': TaskManager.get_current_index(),
                'history_length': total
            }), 400
        
        return jsonify({**state, 'workspace': TaskManager.get_workspace()}), 200
    except ValueError as e:
        logger.warning(f"History travel validation error: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as exc:
        logger.error(f"History travel error: {exc}", exc_info=True)
        return jsonify({'error': str(exc)}), 500
@app.route('/api/undo', methods=['POST'])
def undo():
    state = TaskManager.undo()
    if state is None:
        return jsonify({'error': 'Cannot undo.'}), 400
    return jsonify({**state, 'workspace': TaskManager.get_workspace()}), 200
@app.route('/api/redo', methods=['POST'])
def redo():
    state = TaskManager.redo()
    if state is None:
        return jsonify({'error': 'Cannot redo.'}), 400
    return jsonify({**state, 'workspace': TaskManager.get_workspace()}), 200
@app.route('/api/init', methods=['POST'])
def initialize():
    state = TaskManager.initialize()
    return jsonify({'message': 'Workspace reset.', 'state': state, 'workspace': TaskManager.get_workspace()}), 200
@app.route('/health', methods=['GET'])
def health():
    supabase_status = 'unavailable'
    tables_info = {}
    
    if supabase:
        try:
            # Test connection and check tables
            workspace_response = supabase.table('workspace_state').select('*', count='exact').limit(1).execute()
            tasks_response = supabase.table('tasks').select('*', count='exact').limit(1).execute()
            snapshots_response = supabase.table('snapshots').select('*', count='exact').limit(1).execute()
            
            supabase_status = 'connected'
            tables_info = {
                'workspace_state': getattr(workspace_response, 'count', 0),
                'tasks': getattr(tasks_response, 'count', 0),
                'snapshots': getattr(snapshots_response, 'count', 0)
            }
        except Exception as e:
            supabase_status = f'error: {str(e)[:50]}'
            logger.debug(f"Health check Supabase error: {e}")
    
    status = {
        'status': 'healthy' if supabase_status == 'connected' else 'degraded',
        'supabase': supabase_status,
        'storage': 'supabase' if supabase_status == 'connected' else 'file',
        'tables': tables_info,
        'environment': 'production' if is_production else 'development'
    }
    
    # Return 503 if Supabase is expected but not available
    status_code = 200 if supabase_status in ['connected', 'unavailable'] else 503
    return jsonify(status), status_code

@app.route('/api/diagnostic', methods=['GET'])
def diagnostic():
    """Diagnostic endpoint to help troubleshoot Supabase integration"""
    diagnostics = {
        'environment': {
            'supabase_url_set': bool(SUPABASE_URL),
            'supabase_key_set': bool(SUPABASE_ANON_KEY),
            'is_production': is_production,
            'file_storage_path': str(STORE_PATH)
        },
        'supabase': {
            'connected': supabase is not None
        },
        'schema': {}
    }
    
    if supabase:
        try:
            # Check each table
            tables_to_check = ['workspace_state', 'snapshots', 'tasks']
            for table_name in tables_to_check:
                try:
                    response = supabase.table(table_name).select('*', count='exact').limit(1).execute()
                    diagnostics['schema'][table_name] = {
                        'exists': True,
                        'row_count': getattr(response, 'count', 0)
                    }
                except Exception as e:
                    diagnostics['schema'][table_name] = {
                        'exists': False,
                        'error': str(e)
                    }
        except Exception as e:
            diagnostics['supabase']['error'] = str(e)
    
    return jsonify(diagnostics), 200
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
