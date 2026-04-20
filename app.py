from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from threading import RLock
from typing import Any
from uuid import uuid4

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

STORE_PATH = Path(__file__).with_name("data").joinpath("task_state.json")
LOCK = RLock()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clone_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return deepcopy(tasks)


class StateStore:
    @staticmethod
    def _default_state() -> dict[str, Any]:
        empty_snapshot = {
            "id": str(uuid4()),
            "label": "Workspace initialized",
            "created_at": utc_now(),
            "tasks": [],
        }
        return {
            "tasks": [],
            "history": [empty_snapshot],
            "current_index": 0,
        }

    @staticmethod
    def _ensure_store_exists() -> None:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not STORE_PATH.exists():
            STORE_PATH.write_text(json.dumps(StateStore._default_state(), indent=2), encoding="utf-8")

    @staticmethod
    def load() -> dict[str, Any]:
        with LOCK:
            StateStore._ensure_store_exists()
            return json.loads(STORE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def save(state: dict[str, Any]) -> None:
        with LOCK:
            StateStore._ensure_store_exists()
            STORE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

    @staticmethod
    def reset() -> dict[str, Any]:
        state = StateStore._default_state()
        StateStore.save(state)
        return state


class TaskManager:
    @staticmethod
    def get_state() -> dict[str, Any]:
        return StateStore.load()

    @staticmethod
    def get_all_tasks() -> list[dict[str, Any]]:
        return TaskManager.get_state()["tasks"]

    @staticmethod
    def _save_snapshot(state: dict[str, Any], label: str) -> dict[str, Any]:
        history = state["history"][: state["current_index"] + 1]
        snapshot = {
            "id": str(uuid4()),
            "label": label,
            "created_at": utc_now(),
            "tasks": clone_tasks(state["tasks"]),
        }
        history.append(snapshot)
        state["history"] = history
        state["current_index"] = len(history) - 1
        StateStore.save(state)
        return snapshot

    @staticmethod
    def _find_task(tasks: list[dict[str, Any]], task_id: str) -> dict[str, Any] | None:
        return next((task for task in tasks if task["id"] == task_id), None)

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
            raise ValueError("Selected parent task does not exist.")
        if task_id is not None and parent_id == task_id:
            raise ValueError("A task cannot be its own parent.")

        ancestor_id = parent.get("parent_id")
        while ancestor_id:
            if ancestor_id == task_id:
                raise ValueError("This change would create a parent-child cycle.")
            ancestor = TaskManager._find_task(tasks, ancestor_id)
            ancestor_id = ancestor.get("parent_id") if ancestor else None

    @staticmethod
    def create_task(title: str, parent_id: str | None, status: str) -> dict[str, Any]:
        state = TaskManager.get_state()
        tasks = state["tasks"]
        TaskManager._assert_parent_is_valid(tasks, None, parent_id)

        task = {
            "id": str(uuid4()),
            "title": title.strip(),
            "parent_id": parent_id,
            "status": status,
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        tasks.append(task)
        TaskManager._save_snapshot(state, f"Created '{task['title']}'")
        return task

    @staticmethod
    def update_task(task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        state = TaskManager.get_state()
        tasks = state["tasks"]
        task = TaskManager._find_task(tasks, task_id)
        if task is None:
            raise LookupError("Task not found.")

        title = str(payload.get("title", task["title"])).strip()
        status = payload.get("status", task["status"])
        parent_id = payload.get("parent_id", task["parent_id"])
        if parent_id == "":
            parent_id = None

        if not title:
            raise ValueError("Title is required.")
        if status not in {"todo", "in_progress", "done"}:
            raise ValueError("Invalid status.")

        TaskManager._assert_parent_is_valid(tasks, task_id, parent_id)

        task["title"] = title
        task["status"] = status
        task["parent_id"] = parent_id
        task["updated_at"] = utc_now()
        TaskManager._save_snapshot(state, f"Updated '{task['title']}'")
        return task

    @staticmethod
    def _get_descendant_ids(task_id: str, tasks: list[dict[str, Any]]) -> list[str]:
        descendants = [task_id]
        children = [task for task in tasks if task.get("parent_id") == task_id]
        for child in children:
            descendants.extend(TaskManager._get_descendant_ids(child["id"], tasks))
        return descendants

    @staticmethod
    def delete_task(task_id: str) -> dict[str, Any]:
        state = TaskManager.get_state()
        tasks = state["tasks"]
        task = TaskManager._find_task(tasks, task_id)
        if task is None:
            raise LookupError("Task not found.")

        deleted_ids = set(TaskManager._get_descendant_ids(task_id, tasks))
        state["tasks"] = [item for item in tasks if item["id"] not in deleted_ids]
        TaskManager._save_snapshot(state, f"Deleted '{task['title']}' and descendants")
        return {
            "deleted_count": len(deleted_ids),
            "deleted_ids": list(deleted_ids),
            "strategy": "cascade_delete",
        }

    @staticmethod
    def get_history() -> list[dict[str, Any]]:
        history = TaskManager.get_state()["history"]
        return [
            {
                "id": item["id"],
                "label": item["label"],
                "created_at": item["created_at"],
                "task_count": len(item["tasks"]),
            }
            for item in history
        ]

    @staticmethod
    def get_current_index() -> int:
        return TaskManager.get_state()["current_index"]

    @staticmethod
    def travel_to_state(index: int) -> dict[str, Any] | None:
        state = TaskManager.get_state()
        history = state["history"]
        if index < 0 or index >= len(history):
            return None

        snapshot = history[index]
        state["current_index"] = index
        state["tasks"] = clone_tasks(snapshot["tasks"])
        StateStore.save(state)
        return {
            "index": index,
            "snapshot": {
                "id": snapshot["id"],
                "label": snapshot["label"],
                "created_at": snapshot["created_at"],
                "task_count": len(snapshot["tasks"]),
            },
            "tasks": state["tasks"],
        }

    @staticmethod
    def undo() -> dict[str, Any] | None:
        return TaskManager.travel_to_state(TaskManager.get_current_index() - 1)

    @staticmethod
    def redo() -> dict[str, Any] | None:
        return TaskManager.travel_to_state(TaskManager.get_current_index() + 1)

    @staticmethod
    def initialize() -> dict[str, Any]:
        return StateStore.reset()


@app.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html")


@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    tasks = sorted(TaskManager.get_all_tasks(), key=lambda item: item["created_at"])
    return jsonify({"tasks": tasks, "strategy": "cascade_delete"}), 200


@app.route("/api/tasks", methods=["POST"])
def create_task():
    try:
        data = request.get_json(silent=True) or {}
        title = str(data.get("title", "")).strip()
        parent_id = data.get("parent_id") or None
        status = data.get("status", "todo")
        if not title:
            return jsonify({"error": "Title is required."}), 400
        if status not in {"todo", "in_progress", "done"}:
            return jsonify({"error": "Invalid status."}), 400

        task = TaskManager.create_task(title, parent_id, status)
        return jsonify({"task": task}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/tasks/<task_id>", methods=["PATCH"])
def update_task(task_id: str):
    try:
        data = request.get_json(silent=True) or {}
        task = TaskManager.update_task(task_id, data)
        return jsonify({"task": task}), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id: str):
    try:
        result = TaskManager.delete_task(task_id)
        return jsonify(result), 200
    except LookupError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/history", methods=["GET"])
def get_history():
    history = TaskManager.get_history()
    return jsonify(
        {
            "history": history,
            "current_index": TaskManager.get_current_index(),
            "total": len(history),
        }
    ), 200


@app.route("/api/history/travel", methods=["POST"])
def travel_to_state():
    try:
        data = request.get_json(silent=True) or {}
        if "index" not in data:
            return jsonify({"error": "Index is required."}), 400

        index = int(data["index"])
        state = TaskManager.travel_to_state(index)
        if state is None:
            return jsonify({"error": "Invalid index."}), 400
        return jsonify(state), 200
    except ValueError:
        return jsonify({"error": "Index must be a number."}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/undo", methods=["POST"])
def undo():
    state = TaskManager.undo()
    if state is None:
        return jsonify({"error": "Cannot undo."}), 400
    return jsonify(state), 200


@app.route("/api/redo", methods=["POST"])
def redo():
    state = TaskManager.redo()
    if state is None:
        return jsonify({"error": "Cannot redo."}), 400
    return jsonify(state), 200


@app.route("/api/init", methods=["POST"])
def initialize():
    state = TaskManager.initialize()
    return jsonify({"message": "Workspace reset.", "state": state}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    StateStore._ensure_store_exists()
    app.run(debug=True, host="0.0.0.0", port=5000)
