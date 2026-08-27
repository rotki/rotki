import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useTaskPollingScheduler } from './use-task-polling-scheduler';

const ACTIVE_POLLING_MS = 500;
const IDLE_POLLING_MS = 4000;
const BACKOFF_FACTOR = 1.5;
const SECOND_GAP_MS = ACTIVE_POLLING_MS * BACKOFF_FACTOR;

const monitor = vi.fn();

vi.mock('@/modules/core/tasks/use-task-monitor', () => ({
  useTaskMonitor: (): object => ({ monitor }),
}));

describe('useTaskPollingScheduler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.useFakeTimers();
    monitor.mockResolvedValue(undefined);
    useMainStore().setConnected(true);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const runTask = (): void => {
    useTaskStore().add({ id: 1, label: 'test' });
  };

  it('should not poll while the backend is deliberately down', async () => {
    const { start } = useTaskPollingScheduler();
    runTask();
    start(false);

    useMainStore().setConnected(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS * 10);
    expect(monitor).not.toHaveBeenCalled();
  });

  it('should resume polling on its own once the backend is back, without being restarted', async () => {
    const { start } = useTaskPollingScheduler();
    runTask();
    start(false);

    useMainStore().setConnected(false);
    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS * 4);
    expect(monitor).not.toHaveBeenCalled();

    useMainStore().setConnected(true);
    await vi.advanceTimersByTimeAsync(IDLE_POLLING_MS);
    expect(monitor).toHaveBeenCalled();
  });

  it('should poll slowly while nothing is outstanding', async () => {
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 100);
    expect(monitor).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(IDLE_POLLING_MS);
    expect(monitor).toHaveBeenCalledOnce();
  });

  it('should poll quickly as soon as a task is outstanding', async () => {
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();
  });

  it('should back off while the outstanding work does not change', async () => {
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS);
    expect(monitor).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS - ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(2);
  });

  it('should return to the fast cadence when a task appears, not the next step of the backoff', async () => {
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + SECOND_GAP_MS + 100);
    expect(monitor).toHaveBeenCalledTimes(2);

    useTaskStore().add({ id: 2, label: 'second' });
    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS * BACKOFF_FACTOR + 50);
    expect(monitor).toHaveBeenCalledTimes(3);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(4);
  });

  it('should slow down again once the work is done, from the poll after the one already scheduled', async () => {
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();

    useTaskStore().remove(1);
    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS * 2);
    expect(monitor).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(IDLE_POLLING_MS);
    expect(monitor).toHaveBeenCalledTimes(3);
  });

  it('should not start the next poll until the current one has finished', async () => {
    runTask();
    let release: () => void = () => {};
    monitor.mockImplementation(async () => new Promise<void>((resolve) => {
      release = resolve;
    }));

    const { start } = useTaskPollingScheduler();
    start(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(monitor).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS * 4);
    expect(monitor).toHaveBeenCalledOnce();

    release();
    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(2);
  });

  it('should keep polling after a failed pass', async () => {
    runTask();
    monitor.mockRejectedValueOnce(new Error('boom'));

    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(2);
  });

  it('should poll immediately when asked to', async () => {
    const { start } = useTaskPollingScheduler();
    start(true);

    await vi.advanceTimersByTimeAsync(0);
    expect(monitor).toHaveBeenCalledOnce();
  });

  it('should stop polling', async () => {
    runTask();
    const { start, stop } = useTaskPollingScheduler();
    start(false);
    stop();

    await vi.advanceTimersByTimeAsync(IDLE_POLLING_MS * 2);
    expect(monitor).not.toHaveBeenCalled();
  });
});
