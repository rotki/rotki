import type { Task, TaskMeta } from '@/modules/core/tasks/types';
import { assert } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType } from '@/modules/core/tasks/task-type';

const mockCancelAsyncTask = vi.fn();

vi.mock('@/modules/core/tasks/use-task-api', () => ({
  useTaskApi: vi.fn().mockReturnValue({
    cancelAsyncTask: (...args: unknown[]): unknown => mockCancelAsyncTask(...args),
  }),
}));

function getMeta(overrides?: Partial<TaskMeta>): TaskMeta {
  return { title: 'Test task', ...overrides };
}

function makeTask(id: number, type: TaskType, meta: TaskMeta = getMeta()): Task<TaskMeta> {
  return { id, type, meta, time: Date.now() };
}

describe('useTaskHandler', () => {
  let handler: ReturnType<typeof import('@/modules/core/tasks/use-task-handler').useTaskHandler>;
  let store: ReturnType<typeof import('@/modules/core/tasks/use-task-store').useTaskStore>;

  beforeEach(async () => {
    vi.resetModules();
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();

    const { useTaskStore } = await import('@/modules/core/tasks/use-task-store');
    const { useTaskHandler } = await import('@/modules/core/tasks/use-task-handler');
    store = useTaskStore();
    handler = useTaskHandler();
  });

  describe('runTask', () => {
    it('should return TaskSuccess on successful task', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 1 });

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.TX,
        meta: getMeta(),
      });

      await nextTick();
      handler.handleResult({ result: 'hello', message: '' }, makeTask(1, TaskType.TX));

      const outcome = await promise;

      expect(outcome).toEqual({
        success: true,
        result: 'hello',
        message: undefined,
      });
      expect(taskFn).toHaveBeenCalledOnce();
    });

    it('should return TaskSuccess with message when present', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 2 });

      const promise = handler.runTask<number, TaskMeta>(taskFn, {
        type: TaskType.MANUAL_BALANCES_ADD,
        meta: getMeta(),
      });

      await nextTick();
      handler.handleResult(
        { result: 42, message: 'completed with info' },
        makeTask(2, TaskType.MANUAL_BALANCES_ADD),
      );

      const outcome = await promise;

      expect(outcome).toEqual({
        success: true,
        result: 42,
        message: 'completed with info',
      });
    });

    it('should return TaskFailure with error when result has error field', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 3 });
      const error = new Error('backend exploded');

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.QUERY_BALANCES,
        meta: getMeta(),
      });

      await nextTick();
      handler.handleResult(
        { result: null, message: '', error },
        makeTask(3, TaskType.QUERY_BALANCES),
      );

      const outcome = await promise;

      assert(!outcome.success);
      expect(outcome.message).toBe('backend exploded');
      expect(outcome.error).toBe(error);
      expect(outcome.cancelled).toBe(false);
      expect(outcome.backendCancelled).toBe(false);
      expect(outcome.skipped).toBe(false);
    });

    it('should return cancelled when user cancels task', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 4 });

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.IMPORT_CSV,
        meta: getMeta(),
      });

      await nextTick();
      handler.handleResult(
        { result: null, message: 'task_cancelled_by_user' },
        makeTask(4, TaskType.IMPORT_CSV),
      );

      const outcome = await promise;

      assert(!outcome.success);
      expect(outcome.cancelled).toBe(true);
      expect(outcome.backendCancelled).toBe(false);
      expect(outcome.skipped).toBe(false);
    });

    it('should return backendCancelled when result is null with no message', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 5 });

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.QUERY_EXCHANGE_BALANCES,
        meta: getMeta(),
      });

      await nextTick();
      handler.handleResult(
        { result: null, message: '' },
        makeTask(5, TaskType.QUERY_EXCHANGE_BALANCES),
      );

      const outcome = await promise;

      assert(!outcome.success);
      expect(outcome.cancelled).toBe(true);
      expect(outcome.backendCancelled).toBe(true);
      expect(outcome.skipped).toBe(false);
    });

    it('should return error when result is null with a non-cancel message', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 6 });

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.TX,
        meta: getMeta(),
      });

      await nextTick();
      handler.handleResult(
        { result: null, message: 'something went wrong' },
        makeTask(6, TaskType.TX),
      );

      const outcome = await promise;

      assert(!outcome.success);
      expect(outcome.message).toBe('something went wrong');
      expect(outcome.cancelled).toBe(false);
      expect(outcome.backendCancelled).toBe(false);
      expect(outcome.skipped).toBe(false);
    });

    it('should skip when guard detects duplicate task', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 7 });

      store.addTask(99, TaskType.TX, getMeta());

      const outcome = await handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.TX,
        meta: getMeta(),
      });

      assert(!outcome.success);
      expect(outcome.skipped).toBe(true);
      expect(outcome.cancelled).toBe(false);
      expect(outcome.backendCancelled).toBe(false);
      expect(taskFn).not.toHaveBeenCalled();
    });

    it('should not skip when guard is disabled', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 8 });

      store.addTask(99, TaskType.TX, getMeta());

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.TX,
        meta: getMeta(),
        guard: false,
      });

      expect(taskFn).toHaveBeenCalledOnce();

      await nextTick();
      handler.handleResult({ result: 'ok', message: '' }, makeTask(8, TaskType.TX));

      const outcome = await promise;
      expect(outcome.success).toBe(true);
    });

    it('should use per-taskId handler when unique is false', async () => {
      const taskFnA = vi.fn().mockResolvedValue({ taskId: 10 });
      const taskFnB = vi.fn().mockResolvedValue({ taskId: 11 });
      const meta = getMeta();

      const promiseA = handler.runTask<string, TaskMeta>(taskFnA, {
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        meta,
        unique: false,
        guard: false,
      });

      const promiseB = handler.runTask<string, TaskMeta>(taskFnB, {
        type: TaskType.QUERY_BLOCKCHAIN_BALANCES,
        meta,
        unique: false,
        guard: false,
      });

      await nextTick();

      handler.handleResult(
        { result: 'B', message: '' },
        makeTask(11, TaskType.QUERY_BLOCKCHAIN_BALANCES, meta),
      );

      const outcomeB = await promiseB;
      expect(outcomeB).toEqual({ success: true, result: 'B', message: undefined });

      handler.handleResult(
        { result: 'A', message: '' },
        makeTask(10, TaskType.QUERY_BLOCKCHAIN_BALANCES, meta),
      );

      const outcomeA = await promiseA;
      expect(outcomeA).toEqual({ success: true, result: 'A', message: undefined });
    });

    it('should add task to store after task function resolves', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 20 });

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.TX,
        meta: getMeta(),
      });

      await nextTick();

      expect(store.isTaskRunning(TaskType.TX)).toBe(true);

      // Clean up the pending promise
      handler.handleResult({ result: '', message: '' }, makeTask(20, TaskType.TX));
      await promise;
    });

    it('should skip ignoreResult tasks in handleResult', () => {
      const meta: TaskMeta = { title: 'ignored', ignoreResult: true };
      store.addTask(30, TaskType.TX, meta);

      handler.handleResult({ result: 'anything', message: '' }, makeTask(30, TaskType.TX, meta));

      expect(store.isTaskRunning(TaskType.TX)).toBe(false);
    });
  });

  describe('cancelTask', () => {
    it('should cancel a running task and trigger handler', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 40 });
      mockCancelAsyncTask.mockResolvedValue(true);

      const promise = handler.runTask<string, TaskMeta>(taskFn, {
        type: TaskType.TX,
        meta: getMeta(),
      });

      await nextTick();

      const task = get(store.tasks).find(t => t.id === 40)!;
      expect(task).toBeDefined();

      const deleted = await handler.cancelTask(task);

      expect(deleted).toBe(true);
      expect(mockCancelAsyncTask).toHaveBeenCalledWith(40);

      const outcome = await promise;
      assert(!outcome.success);
      expect(outcome.cancelled).toBe(true);
    });

    it('should return false when task is not running', async () => {
      const task = makeTask(999, TaskType.TX);
      const deleted = await handler.cancelTask(task);
      expect(deleted).toBe(false);
      expect(mockCancelAsyncTask).not.toHaveBeenCalled();
    });

    it('should handle TaskNotFoundError by removing task', async () => {
      store.addTask(50, TaskType.TX, getMeta());
      const { TaskNotFoundError: TNFError } = await import('@/modules/core/tasks/types');
      mockCancelAsyncTask.mockRejectedValue(new TNFError('not found'));

      const task = get(store.tasks).find(t => t.id === 50)!;
      const deleted = await handler.cancelTask(task);

      expect(deleted).toBe(false);
      expect(store.isTaskRunning(TaskType.TX)).toBe(false);
    });

    it('should remove task without handler when cancel succeeds but no handler registered', async () => {
      store.addTask(60, TaskType.MANUAL_BALANCES_ADD, getMeta());
      mockCancelAsyncTask.mockResolvedValue(true);

      const task = get(store.tasks).find(t => t.id === 60)!;
      const deleted = await handler.cancelTask(task);

      expect(deleted).toBe(true);
      expect(store.isTaskRunning(TaskType.MANUAL_BALANCES_ADD)).toBe(false);
    });
  });

  describe('cancelTaskByTaskType', () => {
    it('should cancel all tasks of given types', async () => {
      mockCancelAsyncTask.mockResolvedValue(true);

      store.addTask(70, TaskType.TX, getMeta());
      store.addTask(71, TaskType.TX, getMeta());
      store.addTask(72, TaskType.MANUAL_BALANCES_ADD, getMeta());

      await handler.cancelTaskByTaskType([TaskType.TX]);

      expect(mockCancelAsyncTask).toHaveBeenCalledTimes(2);
      expect(mockCancelAsyncTask).toHaveBeenCalledWith(70);
      expect(mockCancelAsyncTask).toHaveBeenCalledWith(71);
    });

    it('should accept single task type', async () => {
      mockCancelAsyncTask.mockResolvedValue(true);
      store.addTask(80, TaskType.IMPORT_CSV, getMeta());

      await handler.cancelTaskByTaskType(TaskType.IMPORT_CSV);

      expect(mockCancelAsyncTask).toHaveBeenCalledWith(80);
    });
  });
});
