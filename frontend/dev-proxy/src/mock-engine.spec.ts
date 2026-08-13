import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { createMockEngine, DEFAULT_TASK_COMPLETION_MS, type MockedAsyncCalls, type MockRequest } from './mock-engine';

function request(method: string, url: string, body?: unknown): MockRequest {
  return { body, method, path: url.split('?')[0], url };
}

/** Reads the task id out of an async-query response, failing loudly if it is not there. */
function taskIdOf(response: unknown): number {
  assert(typeof response === 'object' && response !== null);
  const result = Reflect.get(response, 'result');
  assert(typeof result === 'object' && result !== null);
  const taskId = Reflect.get(result, 'task_id');
  assert(typeof taskId === 'number');
  return taskId;
}

const UPDATES = '/api/1/assets/updates';

describe('mock engine', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('mock selection', () => {
    it('should answer with the mock declared for the path and method', () => {
      const engine = createMockEngine({ [UPDATES]: { GET: { message: '', result: 5 } } });

      expect(engine.transformResponse(request('GET', UPDATES), { result: 'backend' }))
        .toStrictEqual({ message: '', result: 5 });
    });

    it('should not answer for another method on a mocked path', () => {
      const engine = createMockEngine({ [UPDATES]: { GET: { result: 5 } } });

      expect(engine.transformResponse(request('POST', UPDATES), { result: 'backend' })).toBeUndefined();
    });

    it('should not let a mock answer for a path it merely starts with', () => {
      // The old match was `mockKey.includes(requestPath)`, so a mock declared
      // for /api/1/assets/updates also answered /api/1/assets, and with several
      // matching keys the first declared one won.
      const engine = createMockEngine({ [UPDATES]: { GET: { result: 'wrong' } } });

      expect(engine.transformResponse(request('GET', '/api/1/assets'), { result: 'backend' })).toBeUndefined();
    });

    it('should match a mock key that pins a query string', () => {
      const engine = createMockEngine({ [`${UPDATES}?limit=1`]: { GET: { result: 'pinned' } } });

      expect(engine.transformResponse(request('GET', `${UPDATES}?limit=1`), {})).toStrictEqual({ result: 'pinned' });
    });

    it('should leave an unmocked request to the backend', () => {
      const engine = createMockEngine({});

      expect(engine.transformResponse(request('GET', '/api/1/settings'), { result: 'backend' })).toBeUndefined();
    });
  });

  describe('array mocks', () => {
    const mocks: MockedAsyncCalls = {
      [UPDATES]: { GET: [{ result: 1 }, { result: 2 }] },
    };

    it('should serve one entry per call and repeat the last', () => {
      const engine = createMockEngine(mocks);

      expect(engine.transformResponse(request('GET', UPDATES), {})).toStrictEqual({ result: 1 });
      expect(engine.transformResponse(request('GET', UPDATES), {})).toStrictEqual({ result: 2 });
      expect(engine.transformResponse(request('GET', UPDATES), {})).toStrictEqual({ result: 2 });
    });

    it('should advance the same cursor whatever query string the url carries', () => {
      // The cursor used to be keyed on the full url in one branch and on the
      // path in another, so the same endpoint advanced two separate counters.
      const engine = createMockEngine(mocks);

      expect(engine.transformResponse(request('GET', UPDATES), {})).toStrictEqual({ result: 1 });
      expect(engine.transformResponse(request('GET', `${UPDATES}?upgrade=1`), {})).toStrictEqual({ result: 2 });
    });

    it('should keep a separate cursor per method', () => {
      const engine = createMockEngine({
        [UPDATES]: { GET: [{ result: 'get-1' }], POST: [{ result: 'post-1' }] },
      });

      expect(engine.transformResponse(request('GET', UPDATES), {})).toStrictEqual({ result: 'get-1' });
      expect(engine.transformResponse(request('POST', UPDATES), {})).toStrictEqual({ result: 'post-1' });
    });
  });

  describe('async queries', () => {
    const mocks: MockedAsyncCalls = { [UPDATES]: { POST: { message: '', result: 'done' } } };

    it('should answer an async_query body with a task id', () => {
      const engine = createMockEngine(mocks);

      const response = engine.transformResponse(request('POST', UPDATES, { async_query: true }), {});

      expect(response).toStrictEqual({ message: '', result: { task_id: expect.any(Number) } });
      engine.stop();
    });

    it('should answer an async_query url parameter with a task id', () => {
      const engine = createMockEngine(mocks);

      const response = engine.transformResponse(request('POST', `${UPDATES}?async_query=true`), {});

      expect(response).toStrictEqual({ message: '', result: { task_id: expect.any(Number) } });
      engine.stop();
    });

    it('should serve the mock directly when the request is not an async query', () => {
      const engine = createMockEngine(mocks);

      expect(engine.transformResponse(request('POST', UPDATES, { async_query: false }), {}))
        .toStrictEqual({ message: '', result: 'done' });
    });

    it('should report the task as pending, then completed with its outcome', () => {
      const engine = createMockEngine(mocks);
      const created = engine.transformResponse(request('POST', UPDATES, { async_query: true }), {});
      const taskId = taskIdOf(created);

      expect(engine.transformResponse(request('GET', `/api/1/tasks/${taskId}`), {}))
        .toStrictEqual({ message: '', result: { outcome: null, status: 'pending' } });

      vi.advanceTimersByTime(DEFAULT_TASK_COMPLETION_MS);

      expect(engine.transformResponse(request('GET', `/api/1/tasks/${taskId}`), {}))
        .toStrictEqual({ message: '', result: { outcome: { message: '', result: 'done' }, status: 'completed' } });
    });

    it('should hand a completed task outcome out only once', () => {
      const engine = createMockEngine(mocks);
      const created = engine.transformResponse(request('POST', UPDATES, { async_query: true }), {});
      const taskId = taskIdOf(created);
      vi.advanceTimersByTime(DEFAULT_TASK_COMPLETION_MS);
      engine.transformResponse(request('GET', `/api/1/tasks/${taskId}`), {});

      expect(engine.transformResponse(request('GET', `/api/1/tasks/${taskId}`), { result: 'backend' })).toBeUndefined();
    });

    it('should leave a task it never created to the backend', () => {
      const engine = createMockEngine(mocks);

      expect(engine.transformResponse(request('GET', '/api/1/tasks/42'), { result: 'backend' })).toBeUndefined();
    });
  });

  describe('task status', () => {
    const mocks: MockedAsyncCalls = { [UPDATES]: { POST: { result: 'done' } } };

    it('should add its pending tasks to the ones the backend reports', () => {
      const engine = createMockEngine(mocks);
      const created = engine.transformResponse(request('POST', UPDATES, { async_query: true }), {});
      const taskId = taskIdOf(created);

      const status = engine.transformResponse(
        request('GET', '/api/1/tasks/'),
        { message: '', result: { pending: [7], completed: [8] } },
      );

      expect(status).toStrictEqual({ message: '', result: { completed: [8], pending: [7, taskId] } });
      engine.stop();
    });

    it('should report the task as completed once its delay has passed', () => {
      const engine = createMockEngine(mocks);
      const created = engine.transformResponse(request('POST', UPDATES, { async_query: true }), {});
      const taskId = taskIdOf(created);

      vi.advanceTimersByTime(DEFAULT_TASK_COMPLETION_MS);

      expect(engine.transformResponse(request('GET', '/api/1/tasks/'), { message: '', result: {} }))
        .toStrictEqual({ message: '', result: { completed: [taskId], pending: [] } });
    });

    it('should still answer when the backend reports no task lists at all', () => {
      const engine = createMockEngine(mocks);

      expect(engine.transformResponse(request('GET', '/api/1/tasks/'), { message: '', result: null }))
        .toStrictEqual({ message: '', result: { completed: [], pending: [] } });
    });
  });

  describe('handles', () => {
    it('should be true for the task endpoints and for mocked paths only', () => {
      const engine = createMockEngine({ [UPDATES]: { GET: { result: 1 } } });

      expect(engine.handles(request('GET', '/api/1/tasks/'))).toBe(true);
      expect(engine.handles(request('GET', '/api/1/tasks/42'))).toBe(true);
      expect(engine.handles(request('POST', UPDATES))).toBe(true);
      expect(engine.handles(request('GET', '/api/1/settings'))).toBe(false);
    });
  });
});
