import consola from 'consola';

export interface MockedAsyncCalls {
  [url: string]: { [method: string]: unknown };
}

export interface MockRequest {
  method: string;
  /** Path plus query string, as it arrived. */
  url: string;
  /** Path only. */
  path: string;
  /** Parsed request body, when there was one. */
  body?: unknown;
}

export interface MockEngine {
  /**
   * Whether this request can produce a rewritten response. The server only
   * buffers a backend response when this is true, so everything else (exports,
   * downloads) still streams through untouched.
   */
  handles: (req: MockRequest) => boolean;
  /** Whether the request path has a mock declared, in any method. */
  isMocked: (req: MockRequest) => boolean;
  /**
   * The payload to answer with, or undefined to pass the backend response
   * through unchanged.
   */
  transformResponse: (req: MockRequest, backend: unknown) => unknown;
  /** Drops the pending task timers so the process can exit. */
  stop: () => void;
}

export const TASKS_PATH = '/api/1/tasks';

/** How long a mocked async query stays pending before it reports as completed. */
export const DEFAULT_TASK_COMPLETION_MS = 8000;

function createResult(result: unknown): Record<string, unknown> {
  return {
    message: '',
    result,
  };
}

function isAsyncQuery(req: MockRequest): boolean {
  if (req.url.includes('async_query'))
    return true;

  return typeof req.body === 'object' && req.body !== null && Reflect.get(req.body, 'async_query') === true;
}

export function createMockEngine(
  mocks: MockedAsyncCalls,
  { taskCompletionMs = DEFAULT_TASK_COMPLETION_MS }: { taskCompletionMs?: number } = {},
): MockEngine {
  const pending = new Set<number>();
  const completed = new Set<number>();
  const outcomes = new Map<number, unknown>();
  const timers = new Set<ReturnType<typeof setTimeout>>();
  /** Per endpoint+method cursor into an array-shaped mock. */
  const cursors = new Map<string, number>();
  let nextTaskId = 100000;

  /**
   * Mock keys are matched exactly: on the full url first, so a key may pin a
   * query string, then on the path alone. Matching on a substring would let a
   * mock for one endpoint answer for its prefix.
   */
  function findMock(req: MockRequest): unknown {
    return mocks[req.url]?.[req.method] ?? mocks[req.path]?.[req.method];
  }

  /** Arrays serve one entry per call, then repeat the last one. */
  function resolveMock(req: MockRequest, mock: unknown): unknown {
    if (!Array.isArray(mock))
      return mock;

    const key = `${req.method} ${req.path}`;
    const cursor = cursors.get(key) ?? 0;
    cursors.set(key, cursor + 1);
    return mock[Math.min(cursor, mock.length - 1)];
  }

  function createTask(response: unknown): number {
    const taskId = nextTaskId++;
    pending.add(taskId);
    outcomes.set(taskId, response);

    const timer = setTimeout(() => {
      pending.delete(taskId);
      completed.add(taskId);
      timers.delete(timer);
      consola.log(`mock task ${taskId} completed`);
    }, taskCompletionMs);
    // A pending mock task must never keep the proxy alive on its own.
    timer.unref?.();
    timers.add(timer);

    consola.log(`mock task ${taskId} pending`);
    return taskId;
  }

  /** Merges the mocked task ids into whatever the backend reports. */
  function mergeTaskStatus(backend: unknown): unknown {
    const data = typeof backend === 'object' && backend !== null ? backend : createResult({});
    const result = Reflect.get(data, 'result');
    const merged = typeof result === 'object' && result !== null ? result : {};
    const backendPending = Reflect.get(merged, 'pending');
    const backendCompleted = Reflect.get(merged, 'completed');

    return {
      ...data,
      result: {
        ...merged,
        pending: [...(Array.isArray(backendPending) ? backendPending : []), ...pending],
        completed: [...(Array.isArray(backendCompleted) ? backendCompleted : []), ...completed],
      },
    };
  }

  /** Answers a poll for one mocked task; a real backend task falls through. */
  function taskOutcome(req: MockRequest): unknown {
    // Non-numeric siblings (/tasks/trigger, /tasks/scheduler) fall through.
    const taskId = Number.parseInt(req.path.replace(`${TASKS_PATH}/`, ''), 10);
    if (Number.isNaN(taskId))
      return undefined;

    if (completed.has(taskId)) {
      const outcome = outcomes.get(taskId);
      outcomes.delete(taskId);
      completed.delete(taskId);
      return createResult({ outcome, status: 'completed' });
    }

    if (pending.has(taskId))
      return createResult({ outcome: null, status: 'pending' });

    return undefined;
  }

  // The app polls `/api/1/tasks`; the old code only recognised the trailing
  // slash form, so the merge never fired against the real frontend.
  function isTaskStatus(req: MockRequest): boolean {
    return req.path === TASKS_PATH || req.path === `${TASKS_PATH}/`;
  }

  function isTaskPoll(req: MockRequest): boolean {
    return req.path.startsWith(`${TASKS_PATH}/`) && !isTaskStatus(req);
  }

  function isMocked(req: MockRequest): boolean {
    return mocks[req.url] !== undefined || mocks[req.path] !== undefined;
  }

  return {
    handles(req: MockRequest): boolean {
      if (isTaskStatus(req) || isTaskPoll(req))
        return true;

      return isMocked(req);
    },
    isMocked,
    stop(): void {
      for (const timer of timers) clearTimeout(timer);
      timers.clear();
    },
    transformResponse(req: MockRequest, backend: unknown): unknown {
      if (isTaskStatus(req))
        return mergeTaskStatus(backend);

      if (isTaskPoll(req))
        return taskOutcome(req);

      const mock = findMock(req);
      if (mock === undefined)
        return undefined;

      const response = resolveMock(req, mock);
      if (isAsyncQuery(req))
        return createResult({ task_id: createTask(response) });

      return response;
    },
  };
}
