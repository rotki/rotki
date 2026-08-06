import { createCustomPinia } from '@test/utils/create-pinia';
import { isErr, isOk } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';

const mockCancelAsyncTask = vi.fn();

vi.mock('@/modules/core/tasks/use-task-api', () => ({
  useTaskApi: vi.fn().mockReturnValue({
    cancelAsyncTask: (...args: unknown[]): unknown => mockCancelAsyncTask(...args),
  }),
}));

describe('useTaskHandler', () => {
  let handler: ReturnType<typeof import('@/modules/core/tasks/use-task-handler').useTaskHandler>;
  let store: ReturnType<typeof import('@/modules/core/tasks/use-task-store').useTaskStore>;
  // built from the same (post-reset) module graph as the handler, otherwise the
  // class identity differs and the handler's `instanceof` check misses
  let cancellationError: (message: string) => Error;

  beforeEach(async () => {
    vi.resetModules();
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();

    const { useTaskStore } = await import('@/modules/core/tasks/use-task-store');
    const { useTaskHandler } = await import('@/modules/core/tasks/use-task-handler');
    const { RequestCancelledError } = await import('@/modules/core/api/request-queue/errors');
    cancellationError = (message: string): Error => new RequestCancelledError(message);
    store = useTaskStore();
    handler = useTaskHandler();
  });

  describe('runTask', () => {
    it('should resolve ok carrying the result on a successful task', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 1 });

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();
      handler.handleResult({ result: 'hello', message: '' }, 1);

      const outcome = await promise;

      assert(isOk(outcome));
      expect(outcome.value).toBe('hello');
      expect(taskFn).toHaveBeenCalledOnce();
    });

    it('should resolve ok and drop the message when a result carries one', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 2 });

      const promise = handler.runTask<number>(taskFn, 'Test task');

      await nextTick();
      handler.handleResult({ result: 42, message: 'completed with info' }, 2);

      const outcome = await promise;

      assert(isOk(outcome));
      expect(outcome.value).toBe(42);
    });

    it('should return a Cancelled error when the task start is cancelled', async () => {
      const taskFn = vi.fn().mockRejectedValue(cancellationError('All requests cancelled'));

      const outcome = await handler.runTask<string>(taskFn, 'Test task');

      assert(isErr(outcome));
      expect(hasTag(outcome.error, 'Cancelled')).toBe(true);
      expect(store.hasRunningTasks).toBe(false);
    });

    it('should return a Cancelled error when the task start is aborted', async () => {
      const taskFn = vi.fn().mockRejectedValue(new DOMException('aborted', 'AbortError'));

      const outcome = await handler.runTask<string>(taskFn, 'Test task');

      assert(isErr(outcome));
      expect(hasTag(outcome.error, 'Cancelled')).toBe(true);
    });

    it('should rethrow non-cancellation errors from the task start', async () => {
      const taskFn = vi.fn().mockRejectedValue(new Error('backend exploded'));

      await expect(handler.runTask<string>(taskFn, 'Test task')).rejects.toThrow('backend exploded');
    });

    it('should return a TaskFailed error carrying the cause when the result has an error', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 3 });
      const error = new Error('backend exploded');

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();
      handler.handleResult({ result: null, message: '', error }, 3);

      const outcome = await promise;

      assert(isErr(outcome));
      assert(hasTag(outcome.error, 'TaskFailed'));
      expect(outcome.error.message).toBe('backend exploded');
      expect(outcome.error.cause).toBe(error);
    });

    it('should return a Cancelled error when the user cancels the task', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 4 });

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();
      handler.handleResult({ result: null, message: 'task_cancelled_by_user' }, 4);

      const outcome = await promise;

      assert(isErr(outcome));
      expect(hasTag(outcome.error, 'Cancelled')).toBe(true);
    });

    it('should return a BackendCancelled error when the result is null with no message', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 5 });

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();
      handler.handleResult({ result: null, message: '' }, 5);

      const outcome = await promise;

      assert(isErr(outcome));
      expect(hasTag(outcome.error, 'BackendCancelled')).toBe(true);
    });

    it('should return a TaskFailed error when the result is null with a non-cancel message', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 6 });

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();
      handler.handleResult({ result: null, message: 'something went wrong' }, 6);

      const outcome = await promise;

      assert(isErr(outcome));
      assert(hasTag(outcome.error, 'TaskFailed'));
      expect(outcome.error.message).toBe('something went wrong');
    });

    it('should resolve each concurrent task from its own handler', async () => {
      const taskFnA = vi.fn().mockResolvedValue({ taskId: 10 });
      const taskFnB = vi.fn().mockResolvedValue({ taskId: 11 });

      const promiseA = handler.runTask<string>(taskFnA, 'Test task');
      const promiseB = handler.runTask<string>(taskFnB, 'Test task');

      await nextTick();

      handler.handleResult({ result: 'B', message: '' }, 11);

      const outcomeB = await promiseB;
      assert(isOk(outcomeB));
      expect(outcomeB.value).toBe('B');

      handler.handleResult({ result: 'A', message: '' }, 10);

      const outcomeA = await promiseA;
      assert(isOk(outcomeA));
      expect(outcomeA.value).toBe('A');
    });

    it('should add task to store after task function resolves', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 20 });

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();

      expect(get(store.taskById)[20]).toBeDefined();

      // Clean up the pending promise
      handler.handleResult({ result: '', message: '' }, 20);
      await promise;
    });

    it('should drop the task when nothing is awaiting its result', () => {
      store.addTask(30, 'orphan');

      handler.handleResult({ result: 'anything', message: '' }, 30);

      expect(get(store.taskById)[30]).toBeUndefined();
    });
  });

  describe('cancelTaskById', () => {
    it('should cancel a running task and settle its promise cancelled', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 40 });
      mockCancelAsyncTask.mockResolvedValue(true);

      const promise = handler.runTask<string>(taskFn, 'Test task');

      await nextTick();

      const deleted = await handler.cancelTaskById(40);

      expect(deleted).toBe(true);
      expect(mockCancelAsyncTask).toHaveBeenCalledWith(40);
      expect(get(store.taskById)[40]).toBeUndefined();

      const outcome = await promise;
      assert(isErr(outcome));
      expect(hasTag(outcome.error, 'Cancelled')).toBe(true);
    });

    it('should ignore an id with no task in flight', async () => {
      const deleted = await handler.cancelTaskById(999);

      expect(deleted).toBe(false);
      expect(mockCancelAsyncTask).not.toHaveBeenCalled();
    });

    it('should ignore a task the store knows but nothing is awaiting', async () => {
      // Only `runTask` registers a handler, so a store entry on its own is not cancellable.
      store.addTask(60, 'Test task');

      const deleted = await handler.cancelTaskById(60);

      expect(deleted).toBe(false);
      expect(mockCancelAsyncTask).not.toHaveBeenCalled();
    });

    it('should handle TaskNotFoundError by removing the task', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 50 });
      const { TaskNotFoundError: TNFError } = await import('@/modules/core/tasks/types');
      mockCancelAsyncTask.mockRejectedValue(new TNFError('not found'));

      const pending = handler.runTask<string>(taskFn, 'Test task');
      await nextTick();

      const deleted = await handler.cancelTaskById(50);

      expect(deleted).toBe(false);
      expect(get(store.taskById)[50]).toBeUndefined();

      // The promise is still live: only a reported result settles it.
      handler.handleResult({ result: null, message: 'gone' }, 50);
      await pending;
    });

    it('should leave the task alone when the backend refuses the cancel', async () => {
      const taskFn = vi.fn().mockResolvedValue({ taskId: 55 });
      mockCancelAsyncTask.mockResolvedValue(false);

      const pending = handler.runTask<string>(taskFn, 'Test task');
      await nextTick();

      const deleted = await handler.cancelTaskById(55);

      expect(deleted).toBe(false);
      expect(get(store.taskById)[55]).toBeDefined();

      handler.handleResult({ result: 'landed anyway', message: '' }, 55);
      await pending;
    });
  });
});
