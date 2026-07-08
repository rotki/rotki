import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTaskPollingScheduler } from './use-task-polling-scheduler';

interface SchedulerOptions {
  callback: () => void;
  intervalMs: number;
}

let capturedOptions: SchedulerOptions | undefined;
const schedulerStart = vi.fn();
const schedulerStop = vi.fn();
const monitor = vi.fn();

vi.mock('./use-interval-scheduler', () => ({
  useIntervalScheduler: (options: SchedulerOptions): object => {
    capturedOptions = options;
    return { start: schedulerStart, stop: schedulerStop };
  },
}));

vi.mock('@/modules/core/tasks/use-task-monitor', () => ({
  useTaskMonitor: (): object => ({ monitor }),
}));

describe('useTaskPollingScheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOptions = undefined;
  });

  it('should poll every four seconds using the task monitor', () => {
    useTaskPollingScheduler();
    expect(capturedOptions?.intervalMs).toBe(4000);
    expect(capturedOptions?.callback).toBe(monitor);
  });

  it('should delegate start and stop to the interval scheduler', () => {
    const { start, stop } = useTaskPollingScheduler();
    start(true);
    expect(schedulerStart).toHaveBeenCalledWith(true);
    stop();
    expect(schedulerStop).toHaveBeenCalledOnce();
  });
});
