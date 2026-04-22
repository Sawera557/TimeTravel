const state = {
  tasks: [],
  history: [],
  currentIndex: 0,
  latestIndex: 0,
  selectedTaskId: null,
};

const elements = {
  createForm: document.getElementById("create-form"),
  titleInput: document.getElementById("task-title"),
  parentSelect: document.getElementById("task-parent"),
  statusSelect: document.getElementById("task-status"),
  taskCanvas: document.getElementById("task-canvas"),
  undoButton: document.getElementById("undo-button"),
  redoButton: document.getElementById("redo-button"),
  resetButton: document.getElementById("reset-button"),
  slider: document.getElementById("history-slider"),
  historyList: document.getElementById("history-list"),
  timelineLabel: document.getElementById("timeline-label"),
  timelineTime: document.getElementById("timeline-time"),
  historyModeNote: document.getElementById("history-mode-note"),
  statTotal: document.getElementById("stat-total"),
  statRoot: document.getElementById("stat-root"),
  statChildren: document.getElementById("stat-children"),
  statSnapshot: document.getElementById("stat-snapshot"),
  emptyInspector: document.getElementById("empty-inspector"),
  editForm: document.getElementById("edit-form"),
  editTitle: document.getElementById("edit-title"),
  editParent: document.getElementById("edit-parent"),
  editStatus: document.getElementById("edit-status"),
  inspectorCreated: document.getElementById("inspector-created"),
  inspectorUpdated: document.getElementById("inspector-updated"),
  deleteButton: document.getElementById("delete-button"),
  toast: document.getElementById("toast"),
};

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || "Unexpected request failure.");
    error.status = response.status;
    error.payload = payload;
    throw error;
  }
  return payload;
}

function taskMap() {
  return new Map(state.tasks.map((task) => [task.id, task]));
}

function childMap() {
  const map = new Map();
  state.tasks.forEach((task) => {
    const key = task.parent_id || "root";
    if (!map.has(key)) {
      map.set(key, []);
    }
    map.get(key).push(task);
  });
  map.forEach((tasks) => tasks.sort((a, b) => a.created_at.localeCompare(b.created_at)));
  return map;
}

function formatDate(value) {
  if (!value) {
    return "No timestamp available";
  }
  return new Date(value).toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function showToast(message, isError = false) {
  elements.toast.textContent = message;
  elements.toast.style.background = isError ? "rgba(127, 36, 22, 0.95)" : "rgba(23, 63, 58, 0.94)";
  elements.toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    elements.toast.classList.remove("visible");
  }, 2600);
}

function isLatestSnapshot() {
  return state.currentIndex >= state.latestIndex;
}

function applyWorkspace(workspace, preserveSelection = true) {
  state.tasks = workspace.tasks || [];
  state.history = workspace.history || [];
  state.currentIndex = Number(workspace.current_index || 0);
  state.latestIndex = Number(
    workspace.latest_index ?? Math.max(state.history.length - 1, 0),
  );

  if (preserveSelection && state.selectedTaskId) {
    const stillExists = state.tasks.some((task) => task.id === state.selectedTaskId);
    if (!stillExists) {
      state.selectedTaskId = null;
    }
  }

  renderAll();
}

async function recoverFromMissingTask(error, message) {
  const workspace = error?.payload?.workspace;
  state.selectedTaskId = null;

  if (workspace) {
    applyWorkspace(workspace, false);
  } else {
    await refreshWorkspace(false);
  }

  showToast(message, true);
}

function buildParentOptions(select, selectedValue, currentTaskId = null) {
  const currentMap = taskMap();
  const invalidIds = new Set([currentTaskId]);

  if (currentTaskId) {
    const queue = [currentTaskId];
    while (queue.length) {
      const id = queue.shift();
      state.tasks
        .filter((task) => task.parent_id === id)
        .forEach((child) => {
          if (!invalidIds.has(child.id)) {
            invalidIds.add(child.id);
            queue.push(child.id);
          }
        });
    }
  }

  select.innerHTML = '<option value="">No parent (root task)</option>';
  state.tasks
    .filter((task) => !invalidIds.has(task.id))
    .forEach((task) => {
      const option = document.createElement("option");
      option.value = task.id;
      option.textContent = task.title;
      if (task.id === selectedValue) {
        option.selected = true;
      }
      select.appendChild(option);
    });

  if (selectedValue && !currentMap.has(selectedValue)) {
    select.value = "";
  }
}

function renderStats() {
  const rootCount = state.tasks.filter((task) => !task.parent_id).length;
  elements.statTotal.textContent = String(state.tasks.length);
  elements.statRoot.textContent = String(rootCount);
  elements.statChildren.textContent = String(state.tasks.length - rootCount);
  elements.statSnapshot.textContent = `${state.currentIndex + 1} / ${state.history.length}`;
}

function renderHistoryMode() {
  const viewingPast = !isLatestSnapshot();
  const message = viewingPast
    ? "Viewing an older snapshot. Move to the latest snapshot to create, edit, or delete tasks."
    : "";

  elements.historyModeNote.textContent = message;
  elements.historyModeNote.classList.toggle("hidden", !viewingPast);

  const createDisabled = viewingPast;
  const editDisabled = viewingPast || !state.selectedTaskId;

  elements.titleInput.disabled = createDisabled;
  elements.parentSelect.disabled = createDisabled;
  elements.statusSelect.disabled = createDisabled;
  elements.createForm.querySelector('button[type="submit"]').disabled = createDisabled;

  elements.editTitle.disabled = editDisabled;
  elements.editParent.disabled = editDisabled;
  elements.editStatus.disabled = editDisabled;
  elements.deleteButton.disabled = editDisabled;
  elements.editForm.querySelector('button[type="submit"]').disabled = editDisabled;
}

function renderHistory() {
  const total = Math.max(state.history.length - 1, 0);
  elements.slider.max = String(total);
  elements.slider.value = String(Math.max(state.currentIndex, 0));
  elements.undoButton.disabled = state.currentIndex <= 0;
  elements.redoButton.disabled = state.currentIndex >= state.history.length - 1;

  const activeSnapshot = state.history[state.currentIndex];
  elements.timelineLabel.textContent = activeSnapshot ? activeSnapshot.label : "Workspace initialized";
  elements.timelineTime.textContent = activeSnapshot ? formatDate(activeSnapshot.created_at) : "No actions yet";

  elements.historyList.innerHTML = "";
  state.history.forEach((snapshot, index) => {
    const item = document.createElement("li");
    if (index === state.currentIndex) {
      item.classList.add("active");
    }
    item.innerHTML = `
      <strong>${snapshot.label}</strong>
      <span>${snapshot.task_count} tasks • ${formatDate(snapshot.created_at)}</span>
    `;
    item.addEventListener("click", () => navigateTo(index));
    elements.historyList.appendChild(item);
  });
}

function renderTaskTree(parentId = null, depth = 0, children = childMap()) {
  const siblings = children.get(parentId || "root") || [];
  if (!siblings.length) {
    return null;
  }

  const cluster = document.createElement("div");
  cluster.className = `task-cluster${depth ? " child-cluster" : ""}`;

  siblings.forEach((task) => {
    const card = document.createElement("article");
    card.className = `task-card${task.id === state.selectedTaskId ? " selected" : ""}`;
    card.innerHTML = `
      <div class="task-topline">
        <div>
          <h3 class="task-title">${task.title}</h3>
        </div>
        <div class="task-meta">
          <span class="badge ${task.status}">${task.status.replace("_", " ")}</span>
          <span class="badge depth">Level ${depth + 1}</span>
        </div>
      </div>
      <div class="task-footer">
        <span>${task.parent_id ? "Child task" : "Root task"}</span>
        <button type="button">Inspect</button>
      </div>
    `;
    card.addEventListener("click", () => selectTask(task.id));
    cluster.appendChild(card);

    const descendants = renderTaskTree(task.id, depth + 1, children);
    if (descendants) {
      cluster.appendChild(descendants);
    }
  });

  return cluster;
}

function renderTasks() {
  elements.taskCanvas.innerHTML = "";
  if (!state.tasks.length) {
    elements.taskCanvas.innerHTML = `
      <div class="empty-board">
        Your workspace is empty. Create a root task, attach children, then use the timeline to move between snapshots.
      </div>
    `;
    return;
  }

  const tree = renderTaskTree();
  if (tree) {
    elements.taskCanvas.appendChild(tree);
  }
}

function renderInspector() {
  const task = state.tasks.find((item) => item.id === state.selectedTaskId);
  if (!task) {
    state.selectedTaskId = null;
    elements.emptyInspector.classList.remove("hidden");
    elements.editForm.classList.add("hidden");
    return;
  }

  elements.emptyInspector.classList.add("hidden");
  elements.editForm.classList.remove("hidden");
  elements.editTitle.value = task.title;
  elements.editStatus.value = task.status;
  buildParentOptions(elements.editParent, task.parent_id, task.id);
  elements.inspectorCreated.textContent = `Created ${formatDate(task.created_at)}`;
  elements.inspectorUpdated.textContent = `Updated ${formatDate(task.updated_at)}`;
}

function renderAll() {
  buildParentOptions(elements.parentSelect, "");
  renderStats();
  renderHistory();
  renderTasks();
  renderInspector();
  renderHistoryMode();
}

async function refreshWorkspace(preserveSelection = true) {
  const workspace = await api("/api/workspace");
  applyWorkspace(workspace, preserveSelection);
}

function selectTask(taskId) {
  state.selectedTaskId = taskId;
  renderTasks();
  renderInspector();
  renderHistoryMode();
}

async function navigateTo(index) {
  try {
    const response = await api("/api/history/travel", {
      method: "POST",
      body: JSON.stringify({ index }),
    });
    if (response.workspace) {
      applyWorkspace(response.workspace);
    } else {
      await refreshWorkspace();
    }
    return true;
  } catch (error) {
    // Don't call refreshWorkspace on error - state hasn't changed
    throw error;
  }
}

elements.createForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = {
    title: elements.titleInput.value.trim(),
    parent_id: elements.parentSelect.value || null,
    status: elements.statusSelect.value,
  };

  if (!payload.title) {
    showToast("A title is required.", true);
    return;
  }
  if (!isLatestSnapshot()) {
    showToast("Move to the latest snapshot before creating a task.", true);
    return;
  }

  try {
    const response = await api("/api/tasks", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    elements.createForm.reset();
    state.selectedTaskId = response.task.id;
    if (response.workspace) {
      applyWorkspace(response.workspace);
    } else {
      await refreshWorkspace();
    }
    showToast("Task created.");
  } catch (error) {
    showToast(error.message, true);
  }
});

elements.editForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedTaskId) {
    return;
  }
  if (!isLatestSnapshot()) {
    showToast("Move to the latest snapshot before editing a task.", true);
    return;
  }

  try {
    const response = await api(`/api/tasks/${state.selectedTaskId}`, {
      method: "PATCH",
      body: JSON.stringify({
        title: elements.editTitle.value.trim(),
        parent_id: elements.editParent.value || null,
        status: elements.editStatus.value,
      }),
    });
    if (response.workspace) {
      applyWorkspace(response.workspace);
    } else {
      await refreshWorkspace();
    }
    showToast("Task updated.");
  } catch (error) {
    if (error.status === 404) {
      await recoverFromMissingTask(
        error,
        "That task no longer exists in the current snapshot. The view was refreshed.",
      );
      return;
    }
    showToast(error.message, true);
  }
});

elements.deleteButton.addEventListener("click", async () => {
  if (!state.selectedTaskId) {
    return;
  }
  if (!isLatestSnapshot()) {
    showToast("Move to the latest snapshot before deleting a task.", true);
    return;
  }

  try {
    const response = await api(`/api/tasks/${state.selectedTaskId}`, {
      method: "DELETE",
    });
    state.selectedTaskId = null;
    if (response.workspace) {
      applyWorkspace(response.workspace, false);
    } else {
      await refreshWorkspace(false);
    }
    showToast("Task subtree deleted.");
  } catch (error) {
    if (error.status === 404) {
      await recoverFromMissingTask(
        error,
        "That task was already removed. The view was refreshed.",
      );
      return;
    }
    showToast(error.message, true);
  }
});

elements.undoButton.addEventListener("click", async () => {
  if (state.currentIndex <= 0) {
    return;
  }
  try {
    await navigateTo(state.currentIndex - 1);
    showToast("Moved one snapshot back.");
  } catch (error) {
    showToast(error.message, true);
  }
});

elements.redoButton.addEventListener("click", async () => {
  if (state.currentIndex >= state.history.length - 1) {
    return;
  }
  try {
    await navigateTo(state.currentIndex + 1);
    showToast("Moved one snapshot forward.");
  } catch (error) {
    showToast(error.message, true);
  }
});

elements.resetButton.addEventListener("click", async () => {
  try {
    const response = await api("/api/init", { method: "POST", body: JSON.stringify({}) });
    state.selectedTaskId = null;
    if (response.workspace) {
      applyWorkspace(response.workspace, false);
    } else {
      await refreshWorkspace(false);
    }
    showToast("Workspace reset.");
  } catch (error) {
    showToast(error.message, true);
  }
});

elements.slider.addEventListener("input", async (event) => {
  const index = Number(event.target.value);
  try {
    const result = await navigateTo(index);
    if (!result) {
      // If navigation fails, reset slider to current index
      const currentIndex = state.currentIndex;
      elements.slider.value = String(currentIndex);
      showToast("Could not navigate to that snapshot.", true);
    }
  } catch (error) {
    // Reset slider to current index on error
    const currentIndex = state.currentIndex;
    elements.slider.value = String(currentIndex);
    showToast(error.message, true);
  }
});

window.addEventListener("DOMContentLoaded", async () => {
  try {
    await refreshWorkspace(false);
  } catch (error) {
    showToast(error.message, true);
  }
});
