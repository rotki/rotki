/**
 * Rotki Async Task Tracker - DevTools Panel
 * Tracks and correlates async task requests with their results
 */
(function () {
  'use strict';

  // ============================================================================
  // Types
  // ============================================================================

  /**
   * @typedef {'pending' | 'completed' | 'error'} TaskStatus
   */

  /**
   * @typedef {Object} Task
   * @property {number} id - The task ID from the API
   * @property {string} endpoint - The API endpoint path
   * @property {string|null} fullUrl - Full URL of the initial request
   * @property {string} method - HTTP method (GET, POST, etc.)
   * @property {Object|string|null} requestBody - Request body if present
   * @property {Object<string, string>} queryParams - URL query parameters
   * @property {TaskStatus} status - Current task status
   * @property {number} startTime - Start timestamp in milliseconds
   * @property {number|null} endTime - End timestamp in milliseconds
   * @property {number|null} duration - Duration in milliseconds
   * @property {*} response - Task response outcome
   * @property {string|null} error - Error message if failed
   * @property {string|null} taskResultUrl - URL of the task result request
   * @property {Object|null} rawResponse - Raw API response
   */

  /**
   * @typedef {Object} ApiResponse
   * @property {Object} [result] - Result object
   * @property {number} [result.task_id] - Task ID for async requests
   * @property {*} [result.outcome] - Task outcome
   * @property {string} [message] - Error message
   */

  // ============================================================================
  // State
  // ============================================================================

  /** @type {Map<number, Task>} */
  const tasks = new Map();

  /** @type {number|null} */
  let selectedTaskId = null;

  /** @type {boolean} */
  let isRecording = true;

  // ============================================================================
  // DOM References
  // ============================================================================

  /**
   * @typedef {Object} Elements
   * @property {HTMLDivElement} taskList
   * @property {HTMLDivElement} detailPanel
   * @property {HTMLInputElement} filterInput
   * @property {HTMLInputElement} showCompleted
   * @property {HTMLInputElement} showPending
   * @property {HTMLElement} pendingCount
   * @property {HTMLElement} completedCount
   * @property {HTMLButtonElement} clearBtn
   * @property {HTMLButtonElement} exportBtn
   * @property {HTMLButtonElement} recordBtn
   * @property {HTMLDivElement} recordingIndicator
   */

  /** @type {Elements} */
  const elements = {
    taskList: /** @type {HTMLDivElement} */ (document.getElementById('taskList')),
    detailPanel: /** @type {HTMLDivElement} */ (document.getElementById('detailPanel')),
    filterInput: /** @type {HTMLInputElement} */ (document.getElementById('filterInput')),
    showCompleted: /** @type {HTMLInputElement} */ (document.getElementById('showCompleted')),
    showPending: /** @type {HTMLInputElement} */ (document.getElementById('showPending')),
    pendingCount: /** @type {HTMLElement} */ (document.getElementById('pendingCount')),
    completedCount: /** @type {HTMLElement} */ (document.getElementById('completedCount')),
    clearBtn: /** @type {HTMLButtonElement} */ (document.getElementById('clearBtn')),
    exportBtn: /** @type {HTMLButtonElement} */ (document.getElementById('exportBtn')),
    recordBtn: /** @type {HTMLButtonElement} */ (document.getElementById('recordBtn')),
    recordingIndicator: /** @type {HTMLDivElement} */ (document.getElementById('recordingIndicator')),
  };

  // ============================================================================
  // Utility Functions
  // ============================================================================

  /**
   * Formats a timestamp as a locale time string with milliseconds
   * @param {number} timestamp - Unix timestamp in milliseconds
   * @returns {string} Formatted time string (HH:MM:SS.mmm)
   */
  function formatTime(timestamp) {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  }

  /**
   * Formats a duration in milliseconds to a human-readable string
   * @param {number|null} ms - Duration in milliseconds
   * @returns {string} Formatted duration (e.g., "123ms", "1.50s", "2.00m")
   */
  function formatDuration(ms) {
    if (ms === null) return '-';
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  }

  /**
   * Escapes HTML special characters to prevent XSS
   * @param {string} str - String to escape
   * @returns {string} Escaped string safe for HTML insertion
   */
  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /**
   * Converts a JavaScript object to syntax-highlighted HTML
   * @param {*} obj - Object to highlight
   * @returns {string} HTML string with syntax highlighting spans
   */
  function highlightJson(obj) {
    if (obj === null || obj === undefined) {
      return '<span class="json-null">null</span>';
    }

    const escaped = escapeHtml(JSON.stringify(obj, null, 2));

    return escaped
      // Keys
      .replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
      // String values after colons
      .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
      // String values in arrays
      .replace(/\[(\s*)"([^"]*)"/g, '[$1<span class="json-string">"$2"</span>')
      .replace(/,(\s*)"([^"]*)"(\s*[,\]])/g, ',$1<span class="json-string">"$2"</span>$3')
      // Numbers
      .replace(/: (-?\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/\[(\s*)(-?\d+\.?\d*)/g, '[$1<span class="json-number">$2</span>')
      .replace(/,(\s*)(-?\d+\.?\d*)(\s*[,\]])/g, ',$1<span class="json-number">$2</span>$3')
      // Booleans
      .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>')
      // Null
      .replace(/: (null)/g, ': <span class="json-null">$1</span>')
      // Brackets
      .replace(/([{}\[\]])/g, '<span class="json-bracket">$1</span>');
  }

  // ============================================================================
  // Recording Controls
  // ============================================================================

  /**
   * Toggles the recording state between active and paused
   * @returns {void}
   */
  function toggleRecording() {
    isRecording = !isRecording;
    updateRecordingUI();
  }

  /**
   * Updates the UI to reflect the current recording state
   * @returns {void}
   */
  function updateRecordingUI() {
    const { recordBtn, recordingIndicator } = elements;

    if (isRecording) {
      recordBtn.textContent = 'Pause';
      recordBtn.classList.remove('recording-paused');
      recordingIndicator.classList.remove('paused');
      recordingIndicator.title = 'Recording';
    } else {
      recordBtn.textContent = 'Resume';
      recordBtn.classList.add('recording-paused');
      recordingIndicator.classList.add('paused');
      recordingIndicator.title = 'Paused';
    }
  }

  // ============================================================================
  // Filter Popup (for Network Tab filtering)
  // ============================================================================

  /**
   * Shows a popup with a filter value for copying to the Network tab
   * @param {string} url - The URL to extract the filter path from
   * @returns {void}
   */
  function showFilterPopup(url) {
    /** @type {string} */
    let filterValue;
    try {
      filterValue = new URL(url).pathname;
    } catch {
      filterValue = url;
    }

    let popup = document.getElementById('filter-popup');
    if (!popup) {
      popup = createFilterPopup();
    }

    const input = /** @type {HTMLInputElement} */ (popup.querySelector('.filter-popup-input'));
    input.value = filterValue;
    popup.classList.add('visible');

    setTimeout(() => {
      input.focus();
      input.select();
    }, 50);
  }

  /**
   * Creates the filter popup DOM element with event handlers
   * @returns {HTMLDivElement} The created popup element
   */
  function createFilterPopup() {
    const popup = document.createElement('div');
    popup.id = 'filter-popup';
    popup.innerHTML = `
      <div class="filter-popup-content">
        <div class="filter-popup-header">
          <span>Network Tab Filter</span>
          <button class="filter-popup-close">&times;</button>
        </div>
        <input type="text" class="filter-popup-input" readonly>
        <div class="filter-popup-steps">
          <div class="filter-popup-step">1. Select and copy the filter above (Ctrl+C)</div>
          <div class="filter-popup-step">2. Switch to the <strong>Network</strong> tab</div>
          <div class="filter-popup-step">3. Paste in the filter box (Ctrl+V)</div>
        </div>
      </div>
    `;
    document.body.appendChild(popup);

    popup.querySelector('.filter-popup-close')?.addEventListener('click', () => {
      popup.classList.remove('visible');
    });

    popup.querySelector('.filter-popup-input')?.addEventListener('click', (e) => {
      /** @type {HTMLInputElement} */ (e.target).select();
    });

    popup.addEventListener('click', (e) => {
      if (e.target === popup) {
        popup.classList.remove('visible');
      }
    });

    return popup;
  }

  // ============================================================================
  // Task Management
  // ============================================================================

  /**
   * Creates a new task object from a network request
   * @param {number} taskId - The task ID from the API response
   * @param {string} url - The request URL
   * @param {HAREntry} request - The HAR entry for the request
   * @returns {Task} The created task object
   */
  function createTask(taskId, url, request) {
    /** @type {Object|string|null} */
    let requestBody = null;
    if (request.request.postData?.text) {
      try {
        requestBody = JSON.parse(request.request.postData.text);
      } catch {
        requestBody = request.request.postData.text;
      }
    }

    const urlObj = new URL(url);
    return {
      id: taskId,
      endpoint: urlObj.pathname,
      fullUrl: url,
      method: request.request.method,
      requestBody,
      queryParams: Object.fromEntries(urlObj.searchParams),
      status: 'pending',
      startTime: new Date(request.startedDateTime).getTime(),
      endTime: null,
      duration: null,
      response: null,
      error: null,
      taskResultUrl: null,
      rawResponse: null,
    };
  }

  /**
   * Updates an existing task with the result data
   * @param {Task} task - The task to update
   * @param {ApiResponse} data - The API response data
   * @param {HAREntry} request - The HAR entry for the result request
   * @param {string} url - The result request URL
   * @returns {void}
   */
  function updateTaskWithResult(task, data, request, url) {
    const endTime = new Date(request.startedDateTime).getTime() + request.time;
    const hasError = data.result?.outcome === null && data.message;

    task.status = hasError ? 'error' : 'completed';
    task.endTime = endTime;
    task.duration = endTime - task.startTime;
    task.response = data.result?.outcome;
    task.error = hasError ? data.message : null;
    task.rawResponse = data;
    task.taskResultUrl = url;
  }

  /**
   * Creates a task for a result that arrived before the initial request was tracked
   * @param {number} taskId - The task ID
   * @param {ApiResponse} data - The API response data
   * @param {HAREntry} request - The HAR entry for the result request
   * @param {string} url - The result request URL
   * @returns {Task} The created orphan task
   */
  function createOrphanTask(taskId, data, request, url) {
    const endTime = new Date(request.startedDateTime).getTime() + request.time;
    const hasError = data.result?.outcome === null && data.message;

    return {
      id: taskId,
      endpoint: '(unknown - task started before tracking)',
      fullUrl: null,
      method: 'GET',
      requestBody: null,
      queryParams: {},
      status: hasError ? 'error' : 'completed',
      startTime: endTime - (request.time || 0),
      endTime,
      duration: request.time || null,
      response: data.result?.outcome,
      error: hasError ? data.message : null,
      rawResponse: data,
      taskResultUrl: url,
    };
  }

  // ============================================================================
  // Stats
  // ============================================================================

  /**
   * Updates the pending and completed task counts in the UI
   * @returns {void}
   */
  function updateStats() {
    let pending = 0;
    let completed = 0;

    tasks.forEach((task) => {
      if (task.status === 'pending') pending++;
      else completed++;
    });

    elements.pendingCount.textContent = String(pending);
    elements.completedCount.textContent = String(completed);
  }

  // ============================================================================
  // Rendering - Task List
  // ============================================================================

  /**
   * Renders the filtered and sorted task list
   * @returns {void}
   */
  function renderTaskList() {
    const filter = elements.filterInput.value.toLowerCase();
    const showCompletedVal = elements.showCompleted.checked;
    const showPendingVal = elements.showPending.checked;

    const filteredTasks = Array.from(tasks.values())
      .filter((task) => {
        if (task.status === 'pending' && !showPendingVal) return false;
        if ((task.status === 'completed' || task.status === 'error') && !showCompletedVal) return false;
        if (filter) {
          const searchStr = `${task.id} ${task.endpoint}`.toLowerCase();
          if (!searchStr.includes(filter)) return false;
        }
        return true;
      })
      .sort((a, b) => b.startTime - a.startTime);

    if (filteredTasks.length === 0) {
      renderEmptyState();
      return;
    }

    elements.taskList.innerHTML = filteredTasks.map(renderTaskItem).join('');
    bindTaskListEvents();
  }

  /**
   * Renders the empty state message when no tasks match the filter
   * @returns {void}
   */
  function renderEmptyState() {
    const isEmpty = tasks.size === 0;
    elements.taskList.innerHTML = `
      <div class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12,6 12,12 16,14"/>
        </svg>
        <div>${isEmpty ? 'No async tasks recorded yet' : 'No tasks match filter'}</div>
        <div style="margin-top: 8px; font-size: 11px;">
          ${isEmpty ? 'Make requests with asyncQuery=true to see them here' : 'Try adjusting your filter'}
        </div>
      </div>
    `;
    elements.taskList.classList.remove('split');
    elements.detailPanel.style.display = 'none';
  }

  /**
   * Renders a single task item as an HTML string
   * @param {Task} task - The task to render
   * @returns {string} HTML string for the task item
   */
  function renderTaskItem(task) {
    const isSelected = selectedTaskId === task.id ? 'selected' : '';
    const duration = task.duration !== null
      ? `<span class="task-duration"> (${formatDuration(task.duration)})</span>`
      : '';

    return `
      <div class="task-item ${task.status} ${isSelected}" data-task-id="${task.id}">
        <div class="task-header">
          <span class="task-id">Task #${task.id}</span>
          <span class="task-status ${task.status}">${task.status}</span>
        </div>
        <div class="task-endpoint">${task.method} ${task.endpoint}</div>
        <div class="task-time">${formatTime(task.startTime)}${duration}</div>
      </div>
    `;
  }

  /**
   * Binds click event handlers to task list items
   * @returns {void}
   */
  function bindTaskListEvents() {
    elements.taskList.querySelectorAll('.task-item').forEach((el) => {
      el.addEventListener('click', () => {
        selectTask(parseInt(/** @type {HTMLElement} */ (el).dataset.taskId ?? '0', 10));
      });
    });
  }

  // ============================================================================
  // Rendering - Detail Panel
  // ============================================================================

  /**
   * Selects a task and displays its details in the detail panel
   * @param {number} taskId - The ID of the task to select
   * @returns {void}
   */
  function selectTask(taskId) {
    selectedTaskId = taskId;
    const task = tasks.get(taskId);

    elements.taskList.classList.add('split');
    elements.detailPanel.style.display = 'block';

    elements.taskList.querySelectorAll('.task-item').forEach((el) => {
      el.classList.toggle('selected', parseInt(/** @type {HTMLElement} */ (el).dataset.taskId ?? '0', 10) === taskId);
    });

    renderDetailPanel(task);
  }

  /**
   * Renders the detail panel for a selected task
   * @param {Task|undefined} task - The task to display
   * @returns {void}
   */
  function renderDetailPanel(task) {
    if (!task) {
      elements.detailPanel.innerHTML = '';
      return;
    }

    elements.detailPanel.innerHTML = `
      ${renderTaskInfo(task)}
      ${renderNetworkLinks(task)}
      ${renderSection('Query Parameters', 'queryParamsContent', task.queryParams, Object.keys(task.queryParams || {}).length > 0)}
      ${renderSection('Request Body', 'requestBodyContent', task.requestBody, !!task.requestBody)}
      ${renderErrorSection(task)}
      ${renderSection('Response', 'responseContent', task.response, task.response !== null)}
      ${renderSection('Raw Task Response', 'rawResponseContent', task.rawResponse, !!task.rawResponse)}
    `;

    bindDetailPanelEvents();
  }

  /**
   * Renders the task info section HTML
   * @param {Task} task - The task to render info for
   * @returns {string} HTML string for the task info section
   */
  function renderTaskInfo(task) {
    return `
      <div class="detail-section">
        <h3>Task Info</h3>
        <div class="detail-content">
Task ID: ${task.id}
Status: ${task.status}
Endpoint: ${task.endpoint}
Method: ${task.method}
Started: ${formatTime(task.startTime)}
${task.endTime ? `Completed: ${formatTime(task.endTime)}` : ''}
Duration: ${formatDuration(task.duration)}
        </div>
      </div>
    `;
  }

  /**
   * Renders the network links section with buttons to filter in Network tab
   * @param {Task} task - The task to render links for
   * @returns {string} HTML string for the network links section
   */
  function renderNetworkLinks(task) {
    const initialLink = task.fullUrl
      ? renderNetworkLinkButton(task.fullUrl, 'Initial Request')
      : '<span class="network-link-unavailable">Initial request not tracked</span>';

    const resultLink = task.taskResultUrl
      ? renderNetworkLinkButton(task.taskResultUrl, 'Task Response')
      : '<span class="network-link-unavailable">Task response not yet received</span>';

    return `
      <div class="detail-section">
        <h3>Network Links</h3>
        <div class="network-links">${initialLink}${resultLink}</div>
      </div>
    `;
  }

  /**
   * Renders a network link button HTML
   * @param {string} url - The URL for the filter
   * @param {string} label - The button label
   * @returns {string} HTML string for the button
   */
  function renderNetworkLinkButton(url, label) {
    return `
      <button class="network-link-btn" data-url="${encodeURIComponent(url)}" title="Get filter for Network tab">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
        Copy filter: ${label}
      </button>
    `;
  }

  /**
   * Renders a collapsible section with JSON content and a Select All button
   * @param {string} title - Section title
   * @param {string} contentId - ID for the content element
   * @param {*} data - Data to display as JSON
   * @param {boolean} condition - Whether to render the section
   * @returns {string} HTML string for the section, or empty string if condition is false
   */
  function renderSection(title, contentId, data, condition) {
    if (!condition) return '';
    return `
      <div class="detail-section">
        <div class="detail-header">
          <h3>${title}</h3>
          <button class="select-btn" data-target="${contentId}">Select All</button>
        </div>
        <div class="detail-content json" id="${contentId}">${highlightJson(data)}</div>
      </div>
    `;
  }

  /**
   * Renders the error section if the task has an error
   * @param {Task} task - The task to check for errors
   * @returns {string} HTML string for the error section, or empty string
   */
  function renderErrorSection(task) {
    if (!task.error) return '';
    return `
      <div class="detail-section">
        <h3>Error</h3>
        <div class="detail-content" style="color: var(--accent-red);">${task.error}</div>
      </div>
    `;
  }

  /**
   * Binds event handlers for the detail panel buttons
   * @returns {void}
   */
  function bindDetailPanelEvents() {
    // Network link buttons
    elements.detailPanel.querySelectorAll('.network-link-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        showFilterPopup(decodeURIComponent(/** @type {HTMLElement} */ (btn).dataset.url ?? ''));
      });
    });

    // Select all buttons
    elements.detailPanel.querySelectorAll('.select-btn').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const targetEl = document.getElementById(/** @type {HTMLElement} */ (btn).dataset.target ?? '');
        if (targetEl) {
          const range = document.createRange();
          range.selectNodeContents(targetEl);
          const selection = window.getSelection();
          selection?.removeAllRanges();
          selection?.addRange(range);

          btn.textContent = 'Selected!';
          setTimeout(() => { btn.textContent = 'Select All'; }, 1500);
        }
      });
    });
  }

  // ============================================================================
  // Network Request Listener
  // ============================================================================

  /**
   * Handles incoming network requests from the DevTools API
   * @param {HAREntry} request - The HAR entry for the completed request
   * @returns {void}
   */
  function handleNetworkRequest(request) {
    if (!isRecording) return;

    const url = request.request.url;
    if (!url.includes('127.0.0.1') && !url.includes('localhost')) return;

    request.getContent((content) => {
      if (!content) return;

      try {
        const data = /** @type {ApiResponse} */ (JSON.parse(content));
        processResponse(data, url, request);
      } catch {
        // Not JSON, ignore
      }
    });
  }

  /**
   * Processes a parsed API response to track task initiation or completion
   * @param {ApiResponse} data - The parsed response data
   * @param {string} url - The request URL
   * @param {HAREntry} request - The HAR entry for the request
   * @returns {void}
   */
  function processResponse(data, url, request) {
    // Check for async task initiation (returns task_id)
    if (data?.result?.task_id !== undefined) {
      const taskId = data.result.task_id;
      tasks.set(taskId, createTask(taskId, url, request));
      renderTaskList();
      updateStats();
    }

    // Check for task result fetch
    const taskResultMatch = url.match(/\/api\/1\/tasks\/(\d+)$/);
    if (taskResultMatch) {
      const taskId = parseInt(taskResultMatch[1], 10);
      const task = tasks.get(taskId);

      if (task && data?.result) {
        updateTaskWithResult(task, data, request, url);
        renderTaskList();
        updateStats();

        if (selectedTaskId === taskId) {
          renderDetailPanel(task);
        }
      } else if (!task && data?.result?.outcome !== undefined) {
        // Orphan task (started before extension loaded)
        tasks.set(taskId, createOrphanTask(taskId, data, request, url));
        renderTaskList();
        updateStats();
      }
    }
  }

  // ============================================================================
  // Export
  // ============================================================================

  /**
   * Exports all tracked tasks as a JSON file download
   * @returns {void}
   */
  function exportTasks() {
    const exportData = Array.from(tasks.values());
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `rotki-tasks-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    a.click();

    URL.revokeObjectURL(url);
  }

  // ============================================================================
  // Event Binding
  // ============================================================================

  /**
   * Binds all event listeners for the panel
   * @returns {void}
   */
  function bindEvents() {
    elements.filterInput.addEventListener('input', renderTaskList);
    elements.showCompleted.addEventListener('change', renderTaskList);
    elements.showPending.addEventListener('change', renderTaskList);
    elements.recordBtn.addEventListener('click', toggleRecording);
    elements.exportBtn.addEventListener('click', exportTasks);

    elements.clearBtn.addEventListener('click', () => {
      tasks.clear();
      selectedTaskId = null;
      renderTaskList();
      updateStats();
    });

    chrome.devtools.network.onRequestFinished.addListener(handleNetworkRequest);
  }

  // ============================================================================
  // Initialize
  // ============================================================================

  /**
   * Initializes the panel by binding events and rendering initial state
   * @returns {void}
   */
  function init() {
    bindEvents();
    renderTaskList();
    updateStats();
  }

  init();
})();