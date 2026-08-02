import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useTaskPollingScheduler } from './use-task-polling-scheduler';

const ACTIVE_POLLING_MS = 500;
const IDLE_POLLING_MS = 4000;
// The first backed-off gap: 500 · 1.5.
const SECOND_GAP_MS = 750;

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
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const runTask = (): void => {
    useTaskStore().add({ id: 1, label: 'test' });
  };

  it('should poll slowly while nothing is outstanding', async () => {
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 100);
    expect(monitor).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(IDLE_POLLING_MS);
    expect(monitor).toHaveBeenCalledOnce();
  });

  it('should poll quickly as soon as a task is outstanding', async () => {
    // A task's latency is bounded below by this interval, and a capped lane only releases its next
    // slot once the previous task is seen to finish — so the first look paces the whole queue.
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();
  });

  it('should back off while the outstanding work does not change', async () => {
    // Asking eight times a second about a task that has been running for ten seconds answers
    // nothing sooner, so the gap grows until the idle rate.
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();

    // Another fast interval is no longer enough to earn a second poll.
    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS);
    expect(monitor).toHaveBeenCalledOnce();

    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS - ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(2);
  });

  it('should return to the fast cadence when a task appears', async () => {
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + SECOND_GAP_MS + 100);
    expect(monitor).toHaveBeenCalledTimes(2);

    // New work is a sign more is about to happen, so the next gap is the fast one again rather
    // than the third step of the backoff.
    useTaskStore().add({ id: 2, label: 'second' });
    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS * 1.5 + 50);
    expect(monitor).toHaveBeenCalledTimes(3);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(4);
  });

  it('should slow down again once the work is done', async () => {
    runTask();
    const { start } = useTaskPollingScheduler();
    start(false);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS + 50);
    expect(monitor).toHaveBeenCalledOnce();

    // The delay is chosen when a pass finishes, so the poll already scheduled at that point still
    // runs — the slow-down takes effect from the one after it.
    useTaskStore().remove(1);
    await vi.advanceTimersByTimeAsync(SECOND_GAP_MS + 50);
    expect(monitor).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(ACTIVE_POLLING_MS * 2);
    expect(monitor).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(IDLE_POLLING_MS);
    expect(monitor).toHaveBeenCalledTimes(3);
  });

  it('should not start the next poll until the current one has finished', async () => {
    // A fixed interval lets a slow pass overlap the next one and query the same tasks twice.
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
    // Otherwise one rejected poll ends polling for the rest of the session.
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
