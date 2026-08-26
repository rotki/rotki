import { createCustomPinia } from '@test/utils/create-pinia';
import { FetchError } from 'ofetch';
import { beforeEach, describe, expect, it, vi } from 'vitest';

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
    // `result` is asserted, not just `message`: `objectContaining` ignores the field, and
    // anything but `null` sends the handler down its success branch — see the end-to-end case in
    // `use-task-handler.spec.ts`.
    expect(mockHandleResult).toHaveBeenCalledWith(
      {
        message: expect.stringContaining('Task 2 not found'),
        result: null,
      },
      2,
    );
  });

  it('should apply exponential backoff on timeout errors and keep task running', async () => {
    // The timeout path ends with a real `setTimeout(resolve, backoffMs)` (1s on the
    // first retry). Fake timers let us fast-forward that sleep instead of waiting it
    // out in real time; the asserted state is set before the sleep, so coverage is
    // unchanged.
    vi.useFakeTimers();
    try {
      store.addTask(3, 'Test task');

      const timeoutError = new FetchError('The operation was aborted due to timeout');
      mockQueryTasks.mockResolvedValue({ pending: [], completed: [3] });
      mockQueryTaskResult.mockRejectedValue(timeoutError);

      const pending = monitor.monitor();
      await vi.advanceTimersByTimeAsync(1000);
      await pending;

      expect(get(store.taskById)[3]).toBeDefined();
      expect(mockHandleResult).not.toHaveBeenCalled();
      expect(store.getTimeoutCount(3)).toBe(1);
    }
    finally {
      vi.useRealTimers();
    }
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
    // Add a task so monitor runs (hasRunningTasks = true)
    store.addTask(10, 'Test task');

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [10, 999] });
    mockQueryTaskResult.mockResolvedValue({ result: 'ok', message: '' });

    // First call: task 10 is processed, unknown task 999 gets registered
    await monitor.monitor();

    expect(get(store.unknownTasks)).toHaveProperty('999');
    expect(mockQueryTaskResult).toHaveBeenCalledWith(10);

    // Re-add a task so monitor has running tasks
    store.addTask(11, 'Test task');

    // Manually set the unknown task timestamp to be past the threshold (> 30s ago)
    const pastTime = Math.floor(Date.now() / 1000) - 60;
    store.setUnknownTasks({ 999: pastTime });

    mockQueryTasks.mockResolvedValue({ pending: [], completed: [11, 999] });
    mockQueryTaskResult.mockResolvedValue({ result: 'consumed', message: '' });

    await monitor.monitor();

    // Unknown task 999 should have been consumed
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
