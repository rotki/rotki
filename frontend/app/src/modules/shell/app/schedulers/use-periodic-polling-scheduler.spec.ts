import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePeriodicPollingScheduler } from './use-periodic-polling-scheduler';

interface SchedulerOptions {
  callback: () => void;
  intervalMs: number;
}

let capturedOptions: SchedulerOptions | undefined;
const schedulerStart = vi.fn();
const schedulerStop = vi.fn();

const canRequestData = ref<boolean>(false);
const queryPeriod = ref<number>(5);
const connected = ref<boolean>(false);
const check = vi.fn().mockResolvedValue(undefined);
const consume = vi.fn().mockResolvedValue(undefined);

vi.mock('./use-interval-scheduler', () => ({
  useIntervalScheduler: (options: SchedulerOptions): object => {
    capturedOptions = options;
    return { start: schedulerStart, stop: schedulerStop };
  },
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ canRequestData }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'queryPeriod' ? queryPeriod : ref(undefined))),
}));

vi.mock('@/modules/session/use-periodic-data-fetcher', () => ({
  usePeriodicDataFetcher: (): object => ({ check }),
}));

vi.mock('@/modules/core/messaging', () => ({
  useMessageHandling: (): object => ({ consume }),
}));

vi.mock('../use-websocket-connection', () => ({
  useWebsocketConnection: (): object => ({ connected }),
}));

describe('usePeriodicPollingScheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOptions = undefined;
    set(canRequestData, false);
    set(queryPeriod, 5);
    set(connected, false);
  });

  it('should compute the interval from the query period in seconds', () => {
    usePeriodicPollingScheduler();
    expect(capturedOptions?.intervalMs).toBe(5000);
  });

  it('should fetch periodic data when data can be requested', () => {
    set(canRequestData, true);
    usePeriodicPollingScheduler();
    capturedOptions?.callback();
    expect(check).toHaveBeenCalledOnce();
  });

  it('should not fetch periodic data when data cannot be requested', () => {
    set(canRequestData, false);
    usePeriodicPollingScheduler();
    capturedOptions?.callback();
    expect(check).not.toHaveBeenCalled();
  });

  it('should consume messages when the websocket is disconnected', () => {
    set(connected, false);
    usePeriodicPollingScheduler();
    capturedOptions?.callback();
    expect(consume).toHaveBeenCalledOnce();
  });

  it('should not consume messages when the websocket is connected', () => {
    set(connected, true);
    usePeriodicPollingScheduler();
    capturedOptions?.callback();
    expect(consume).not.toHaveBeenCalled();
  });

  it('should delegate start and stop to the interval scheduler', () => {
    const { start, stop } = usePeriodicPollingScheduler();
    start(true);
    expect(schedulerStart).toHaveBeenCalledWith(true);
    stop();
    expect(schedulerStop).toHaveBeenCalledOnce();
  });
});
