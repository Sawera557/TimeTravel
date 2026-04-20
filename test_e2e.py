#!/usr/bin/env python3
"""
End-to-end test suite for the TimeTravel Tasks application.
Tests all core requirements:
1. Task Management (Create, list, update tasks)
2. Task Dependencies (Parent-child relationships)
3. Time-Travel State (Undo/redo, slider navigation)
4. Dependency Handling (cascade delete)
"""

import requests
import json
import sys
from typing import Any, Dict

BASE_URL = "http://localhost:5000"
TESTS_PASSED = 0
TESTS_FAILED = 0


def test(name: str, condition: bool, details: str = "") -> None:
    """Track test results."""
    global TESTS_PASSED, TESTS_FAILED
    if condition:
        TESTS_PASSED += 1
        print(f"[PASS] {name}")
    else:
        TESTS_FAILED += 1
        print(f"[FAIL] {name}")
        if details:
            print(f"       {details}")


def api_get(endpoint: str) -> Dict[str, Any]:
    """Make GET request to API."""
    response = requests.get(f"{BASE_URL}{endpoint}")
    test(f"GET {endpoint} status 200", response.status_code == 200,
         f"Got {response.status_code}")
    return response.json()


def api_post(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make POST request to API."""
    response = requests.post(
        f"{BASE_URL}{endpoint}",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    test(f"POST {endpoint} status 20x", response.status_code in [200, 201],
         f"Got {response.status_code}")
    return response.json()


def api_patch(endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Make PATCH request to API."""
    response = requests.patch(
        f"{BASE_URL}{endpoint}",
        json=data,
        headers={"Content-Type": "application/json"}
    )
    test(f"PATCH {endpoint} status 200", response.status_code == 200,
         f"Got {response.status_code}")
    return response.json()


def api_delete(endpoint: str) -> Dict[str, Any]:
    """Make DELETE request to API."""
    response = requests.delete(f"{BASE_URL}{endpoint}")
    test(f"DELETE {endpoint} status 200", response.status_code == 200,
         f"Got {response.status_code}")
    return response.json()


def main():
    """Run comprehensive test suite."""
    print("=" * 70)
    print("TimeTravel TASKS - END-TO-END TEST SUITE")
    print("=" * 70)
    print()

    # PHASE 1: Health Check
    print("PHASE 1: Health Check")
    print("-" * 70)
    response = requests.get(f"{BASE_URL}/health")
    test("Server is running (/health)", response.status_code == 200)
    data = response.json()
    test("Health status is 'healthy'", data.get("status") == "healthy")
    print()

    # PHASE 2: Initialize Workspace
    print("PHASE 2: Initialize Workspace")
    print("-" * 70)
    init_response = api_post("/api/init", {})
    test("Workspace initializes", "state" in init_response)
    print()

    # PHASE 3: Task Creation
    print("PHASE 3: Task Creation")
    print("-" * 70)

    # Create root task
    task1_response = api_post("/api/tasks", {
        "title": "Project Alpha",
        "parent_id": None,
        "status": "todo"
    })
    test("Create root task", "task" in task1_response)
    task1_id = task1_response.get("task", {}).get("id")
    test("Root task has ID", task1_id is not None)

    # Check tasks list
    tasks_response = api_get("/api/tasks")
    test("GET /api/tasks returns tasks array", "tasks" in tasks_response)
    test("Strategy is cascade_delete",
         tasks_response.get("strategy") == "cascade_delete")
    test("Initial task count is 1", len(tasks_response.get("tasks", [])) == 1)

    print()

    # PHASE 4: Parent-Child Relationships
    print("PHASE 4: Parent-Child Relationships")
    print("-" * 70)

    # Create child task
    task2_response = api_post("/api/tasks", {
        "title": "Backend API",
        "parent_id": task1_id,
        "status": "in_progress"
    })
    test("Create child task", "task" in task2_response)
    task2_id = task2_response.get("task", {}).get("id")
    test("Child task has parent",
         task2_response.get("task", {}).get("parent_id") == task1_id)

    # Verify parent-child relationship
    tasks_response = api_get("/api/tasks")
    test("Task count is now 2", len(tasks_response.get("tasks", [])) == 2)

    # Create another child
    task3_response = api_post("/api/tasks", {
        "title": "Frontend UI",
        "parent_id": task1_id,
        "status": "todo"
    })
    task3_id = task3_response.get("task", {}).get("id")

    tasks_response = api_get("/api/tasks")
    test("Task count is now 3", len(tasks_response.get("tasks", [])) == 3)

    print()

    # PHASE 5: Task Updates
    print("PHASE 5: Task Updates")
    print("-" * 70)

    # Update task title
    update_response = api_patch(f"/api/tasks/{task1_id}", {
        "title": "Project Alpha (Revised)",
        "status": "in_progress"
    })
    test("Update task title",
         update_response.get("task", {}).get("title") == "Project Alpha (Revised)")

    tasks_response = api_get("/api/tasks")
    updated_task = next((t for t in tasks_response["tasks"] if t["id"] == task1_id), None)
    test("Title update persists",
         updated_task and updated_task.get("title") == "Project Alpha (Revised)")

    print()

    # PHASE 6: History & Snapshots
    print("PHASE 6: History & Snapshots")
    print("-" * 70)

    history_response = api_get("/api/history")
    test("History endpoint returns data", "history" in history_response)
    test("History has snapshots", len(history_response.get("history", [])) > 0)
    test("Current index is tracked", "current_index" in history_response)

    snapshot_count = len(history_response.get("history", []))
    test(f"Snapshots created ({snapshot_count})", snapshot_count >= 5)
    # initial + 3 tasks + 1 update = 5

    print()

    # PHASE 7: Undo/Redo
    print("PHASE 7: Undo/Redo")
    print("-" * 70)

    current_index = api_get("/api/history").get("current_index")
    test("Current index before undo", current_index >= 4)

    # Undo
    undo_response = api_post("/api/undo", {})
    test("Undo returns response", undo_response is not None)

    new_index = api_get("/api/history").get("current_index")
    test("Undo decrements index", new_index < current_index)

    # Redo
    redo_response = api_post("/api/redo", {})
    test("Redo returns response", redo_response is not None)

    final_index = api_get("/api/history").get("current_index")
    test("Redo increments index", final_index > new_index)

    print()

    # PHASE 8: Time Travel
    print("PHASE 8: Time Travel")
    print("-" * 70)

    # Travel to earlier snapshot
    travel_response = api_post("/api/history/travel", {"index": 1})
    test("Time travel to index 1", "index" in travel_response)
    test("Time travel returns tasks", "tasks" in travel_response)

    traveled_index = api_get("/api/history").get("current_index")
    test("Time travel sets current index", traveled_index == 1)

    traveled_tasks = api_get("/api/tasks")
    test("Task state reflects time travel",
         len(traveled_tasks.get("tasks", [])) <= 1)

    # Travel back to latest
    history_len = len(api_get("/api/history").get("history", []))
    latest_travel = api_post("/api/history/travel", {"index": history_len - 1})
    test("Travel to latest snapshot", latest_travel is not None)

    print()

    # PHASE 9: Cascade Delete
    print("PHASE 9: Cascade Delete")
    print("-" * 70)

    # Reset to clean state
    api_post("/api/init", {})

    # Create parent with children
    parent = api_post("/api/tasks", {
        "title": "Company",
        "parent_id": None,
        "status": "todo"
    }).get("task", {})
    parent_id = parent.get("id")

    child1 = api_post("/api/tasks", {
        "title": "Department",
        "parent_id": parent_id,
        "status": "todo"
    }).get("task", {})
    child1_id = child1.get("id")

    child2 = api_post("/api/tasks", {
        "title": "Team",
        "parent_id": child1_id,
        "status": "todo"
    }).get("task", {})
    child2_id = child2.get("id")

    tasks_before = api_get("/api/tasks").get("tasks", [])
    test("Created 3-level hierarchy", len(tasks_before) == 3)

    # Delete parent - should cascade delete all descendants
    delete_response = api_delete(f"/api/tasks/{parent_id}")
    test("Delete returns cascade_delete strategy",
         delete_response.get("strategy") == "cascade_delete")
    test("Delete reports correct count",
         delete_response.get("deleted_count") == 3)

    tasks_after = api_get("/api/tasks").get("tasks", [])
    test("All descendants deleted", len(tasks_after) == 0)

    print()

    # PHASE 10: Cycle Prevention
    print("PHASE 10: Cycle Prevention")
    print("-" * 70)

    # Create parent-child pair
    task_a = api_post("/api/tasks", {
        "title": "Task A",
        "parent_id": None,
        "status": "todo"
    }).get("task", {})
    task_a_id = task_a.get("id")

    task_b = api_post("/api/tasks", {
        "title": "Task B",
        "parent_id": task_a_id,
        "status": "todo"
    }).get("task", {})
    task_b_id = task_b.get("id")

    # Try to create cycle
    cycle_response = requests.patch(
        f"{BASE_URL}/api/tasks/{task_a_id}",
        json={"parent_id": task_b_id},
        headers={"Content-Type": "application/json"}
    )
    test("Cycle creation is prevented", cycle_response.status_code != 200,
         f"Status: {cycle_response.status_code}")

    print()

    # PHASE 11: Validation
    print("PHASE 11: Validation")
    print("-" * 70)

    # Empty title validation
    empty_title_response = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"title": "", "status": "todo"},
        headers={"Content-Type": "application/json"}
    )
    test("Empty title rejected", empty_title_response.status_code != 201)

    # Invalid status validation
    invalid_status_response = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"title": "Test", "status": "invalid_status"},
        headers={"Content-Type": "application/json"}
    )
    test("Invalid status rejected", invalid_status_response.status_code != 201)

    print()

    # PHASE 12: Undo Restores Subtree
    print("PHASE 12: Undo Restores Subtree")
    print("-" * 70)

    api_post("/api/init", {})

    # Build a hierarchy
    root = api_post("/api/tasks", {
        "title": "Root",
        "parent_id": None,
        "status": "todo"
    }).get("task", {})
    root_id = root.get("id")

    child = api_post("/api/tasks", {
        "title": "Child",
        "parent_id": root_id,
        "status": "todo"
    }).get("task", {})
    child_id = child.get("id")

    grandchild = api_post("/api/tasks", {
        "title": "Grandchild",
        "parent_id": child_id,
        "status": "todo"
    }).get("task", {})

    test("3-level hierarchy created",
         len(api_get("/api/tasks").get("tasks", [])) == 3)

    # Delete root
    api_delete(f"/api/tasks/{root_id}")
    test("Hierarchy deleted", len(api_get("/api/tasks").get("tasks", [])) == 0)

    # Undo - should restore entire subtree
    api_post("/api/undo", {})
    restored_tasks = api_get("/api/tasks").get("tasks", [])
    test("Undo restores subtree", len(restored_tasks) == 3)

    # Verify parent-child links are intact
    restored_child = next((t for t in restored_tasks if t.get("title") == "Child"), None)
    restored_root = next((t for t in restored_tasks if t.get("title") == "Root"), None)
    test("Parent-child links restored",
         restored_child and restored_child.get("parent_id") == restored_root.get("id"))

    print()

    # Summary
    print("=" * 70)
    print(f"TESTS PASSED: {TESTS_PASSED}")
    print(f"TESTS FAILED: {TESTS_FAILED}")
    print("=" * 70)

    if TESTS_FAILED > 0:
        sys.exit(1)

    print("[SUCCESS] All tests passed!")


if __name__ == "__main__":
    main()


