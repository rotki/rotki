import type { EffectScope, MaybeRefOrGetter } from 'vue';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePeriodicPollingScheduler } from './use-periodic-polling-scheduler';

interface SchedulerOptions {
  callback: () => void;
  intervalMs: MaybeRefOrGetter<number>;
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
    expect(toValue(capturedOptions?.intervalMs)).toBe(5000);
  });

  it('should read the query period when the interval is armed, not when it is built', () => {
    usePeriodicPollingScheduler();
    set(queryPeriod, 12);
    expect(toValue(capturedOptions?.intervalMs)).toBe(12_000);
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

  describe('while the window is hidden', () => {
    let scope: EffectScope;

    /** Builds the scheduler in a scope the test stops, so its visibility watcher cannot outlive it. */
    function build(): ReturnType<typeof usePeriodicPollingScheduler> {
      const scheduler = scope.run(() => usePeriodicPollingScheduler());
      assert(scheduler);
      return scheduler;
    }

    beforeEach(() => {
      set(canRequestData, true);
      setVisibility('visible');
      scope = effectScope();
    });

    afterEach(() => {
      scope.stop();
    });

    it('should skip periodic data but keep consuming messages', () => {
      build();
      setVisibility('hidden');

      capturedOptions?.callback();

      expect(check).not.toHaveBeenCalled();
      expect(consume).toHaveBeenCalledOnce();
    });

    it('should read periodic data once as soon as the window is shown again', async () => {
      const { start } = build();
      start(false);
      setVisibility('hidden');
      await nextTick();

      setVisibility('visible');
      await nextTick();

      expect(check).toHaveBeenCalledOnce();
    });

    it('should not read periodic data on being shown while stopped', async () => {
      const { start, stop } = build();
      start(false);
      stop();
      setVisibility('hidden');
      await nextTick();

      setVisibility('visible');
      await nextTick();

      expect(check).not.toHaveBeenCalled();
    });
  });
});

function setVisibility(state: DocumentVisibilityState): void {
  Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => state });
  document.dispatchEvent(new Event('visibilitychange'));
}
