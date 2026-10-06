import { createCustomPinia } from '@test/utils/create-pinia';
import { FetchError } from 'ofetch';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockQueryTasks = vi.fn();
const mockQueryTaskResult = vi.fn();
const mockHandleResult = vi.fn();

vi.mock('@/modules/core/tasks/use-task-api', () => ({
  useTaskApi: vi.fn().mockReturnValue({
    queryTasks: (...args: unknown[]): unknown => mockQueryTasks(...args),
    queryTaskResult: (...args: unknown[]): unknown => mockQueryTaskResult(...args),
  }),
}));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  useTaskHandler: vi.fn().mockReturnValue({
    handleResult: (...args: unknown[]): unknown => mockHandleResult(...args),
  }),
}));

describe('useTaskMonitor', () => {
  let monitor: ReturnType<typeof import('@/modules/core/tasks/use-task-monitor').useTaskMonitor>;
  let store: ReturnType<typeof import('@/modules/core/tasks/use-task-store').useTaskStore>;

  beforeEach(async () => {
    vi.resetModules();
    setActivePinia(createCustomPinia());
    vi.clearAllMocks();

    const { useTaskStore } = await import('@/modules/core/tasks/use-task-store');
    const { useTaskMonitor } = await import('@/modules/core/tasks/use-task-monitor');
    store = useTaskStore();
    monitor = useTaskMonitor();
  });

  it('should do nothing when there are no running tasks', async () => {
    await monitor.monitor();
    expect(mockQueryTasks).not.toHaveBeenCalled();
  });

  it('should process a completed task', async () => {
    store.addTask(1, 'Test task');
    const taskResult = { result: 'done', message: '' };

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [1] });
    mockQueryTaskResult.mockResolvedValue(taskResult);

    await monitor.monitor();

    expect(mockQueryTasks).toHaveBeenCalledOnce();
    expect(mockQueryTaskResult).toHaveBeenCalledWith(1);
    expect(mockHandleResult).toHaveBeenCalledWith(
      taskResult,
      1,
    );
  });

  it('should not process locked tasks', async () => {
    store.addTask(1, 'Test task');
    store.lock(1);

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [1] });

    await monitor.monitor();

    expect(mockQueryTaskResult).not.toHaveBeenCalled();
    expect(mockHandleResult).not.toHaveBeenCalled();
  });

  it('should handle TaskNotFoundError by removing task and calling error handler', async () => {
    store.addTask(2, 'Test task');

    const { TaskNotFoundError } = await import('@/modules/core/tasks/types');
    mockQueryTasks.mockResolvedValue({ pending: [], completed: [2] });
    mockQueryTaskResult.mockRejectedValue(new TaskNotFoundError('Task 2 not found'));

    await monitor.monitor();

    expect(get(store.taskById)[2]).toBeUndefined();
    expect(mockHandleResult).toHaveBeenCalledWith(
      {
        message: expect.stringContaining('Task 2 not found'),
        result: null,
      },
      2,
    );
  });

  describe('timeout backoff', () => {
    const FIRST_RETRY_DELAY_MS = 1000;

    beforeEach(() => {
      vi.useFakeTimers();
      store.addTask(3, 'Test task');
      mockQueryTasks.mockResolvedValue({ pending: [], completed: [3] });
      mockQueryTaskResult.mockRejectedValue(new FetchError('The operation was aborted due to timeout'));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should keep a timed out task running and count the timeout', async () => {
      await monitor.monitor();

      expect(get(store.taskById)[3]).toBeDefined();
      expect(mockHandleResult).not.toHaveBeenCalled();
      expect(store.getTimeoutCount(3)).toBe(1);
    });

    it('should finish the pass without waiting out the backoff, and skip the task until it ends', async () => {
      await monitor.monitor();
      await monitor.monitor();
      expect(mockQueryTaskResult).toHaveBeenCalledOnce();

      await vi.advanceTimersByTimeAsync(FIRST_RETRY_DELAY_MS);
      await monitor.monitor();

      expect(mockQueryTaskResult).toHaveBeenCalledTimes(2);
    });

    it('should drop a pending retry when the session ends', async () => {
      const { endSession } = await import('@/modules/core/session/session-lifecycle');
      await monitor.monitor();

      endSession();
      await vi.advanceTimersByTimeAsync(FIRST_RETRY_DELAY_MS);

      expect(get(store.locked).has(3)).toBe(true);
    });
  });

  it('should leave a task alone when its result fetch is cancelled, as a logout cancels it', async () => {
    const { RequestCancelledError } = await import('@/modules/core/api/request-queue/errors');
    store.addTask(5, 'Test task');
    mockQueryTasks.mockResolvedValue({ pending: [], completed: [5] });
    mockQueryTaskResult.mockRejectedValue(new RequestCancelledError('No live session'));

    await monitor.monitor();

    expect(mockHandleResult).not.toHaveBeenCalled();
    expect(get(store.locked).has(5)).toBe(false);
  });

  describe('tasks the backend no longer lists', () => {
    it('should settle a task missing from both lists as cancelled by the backend', async () => {
      store.addTask(40, 'Test task');
      mockQueryTasks.mockResolvedValue({ pending: [41], completed: [] });

      await monitor.monitor();

      expect(mockHandleResult).toHaveBeenCalledExactlyOnceWith({ message: '', result: null }, 40);
    });

    it('should not settle a task the backend lists as pending', async () => {
      store.addTask(40, 'Test task');
      mockQueryTasks.mockResolvedValue({ pending: [40], completed: [] });

      await monitor.monitor();

      expect(mockHandleResult).not.toHaveBeenCalled();
    });

    it('should not settle a task added while the listing was in flight', async () => {
      store.addTask(40, 'Test task');
      mockQueryTasks.mockImplementation(async (): Promise<unknown> => {
        store.addTask(42, 'Newer task');
        return { pending: [40], completed: [] };
      });

      await monitor.monitor();

      expect(mockHandleResult).not.toHaveBeenCalled();
    });

    it('should not settle a locked task, whose outcome is being fetched', async () => {
      store.addTask(40, 'Test task');
      store.lock(40);
      mockQueryTasks.mockResolvedValue({ pending: [], completed: [] });

      await monitor.monitor();

      expect(mockHandleResult).not.toHaveBeenCalled();
    });
  });

  it('should remove task and call handler on generic errors', async () => {
    store.addTask(4, 'Test task');
    const genericError = new Error('something broke');

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [4] });
    mockQueryTaskResult.mockRejectedValue(genericError);

    await monitor.monitor();

    expect(get(store.taskById)[4]).toBeUndefined();
    expect(mockHandleResult).toHaveBeenCalledWith(
      expect.objectContaining({
        error: genericError,
        message: 'something broke',
        result: null,
      }),
      4,
    );
  });

  it('should track unknown task ids and consume them past threshold', async () => {
    store.addTask(10, 'Test task');

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [10, 999] });
    mockQueryTaskResult.mockResolvedValue({ result: 'ok', message: '' });

    await monitor.monitor();

    expect(get(store.unknownTasks)).toHaveProperty('999');
    expect(mockQueryTaskResult).toHaveBeenCalledWith(10);

    store.addTask(11, 'Test task');

    const UNKNOWN_TASK_THRESHOLD_SECONDS = 30;
    const pastTheThreshold = Math.floor(Date.now() / 1000) - (UNKNOWN_TASK_THRESHOLD_SECONDS * 2);
    store.setUnknownTasks({ 999: pastTheThreshold });

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [11, 999] });
    mockQueryTaskResult.mockResolvedValue({ result: 'consumed', message: '' });

    await monitor.monitor();

    expect(mockQueryTaskResult).toHaveBeenCalledWith(999);
  });

  it('should process multiple completed tasks', async () => {
    store.addTask(20, 'Test task');
    store.addTask(21, 'Test task');

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [20, 21] });
    mockQueryTaskResult.mockResolvedValue({ result: 'ok', message: '' });

    await monitor.monitor();

    expect(mockQueryTaskResult).toHaveBeenCalledWith(20);
    expect(mockQueryTaskResult).toHaveBeenCalledWith(21);
    expect(mockHandleResult).toHaveBeenCalledTimes(2);
  });

  it('should not run concurrently (re-entrancy guard)', async () => {
    store.addTask(30, 'Test task');

    let resolveQuery: ((value: unknown) => void) | undefined;
    mockQueryTasks.mockImplementation(async (): Promise<unknown> => new Promise((resolve) => {
      resolveQuery = resolve;
    }));

    const first = monitor.monitor();
    const second = monitor.monitor();

    await second;

    resolveQuery?.({ pending: [], completed: [] });
    await first;

    expect(mockQueryTasks).toHaveBeenCalledOnce();
  });
});
