import type { Ref } from 'vue';
import type { OverlayPair } from '@/modules/history/balances/use-accounting-overlay';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskType } from '@/modules/core/tasks/task-type';

const runTaskMock = vi.fn();

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal => ({
  ...(await importOriginal<typeof import('@/modules/core/tasks/use-task-handler')>()),
  useTaskHandler: vi.fn().mockReturnValue({
    runTask: async (taskFn: () => Promise<unknown>, ...rest: unknown[]): Promise<unknown> => runTaskMock(taskFn, ...rest),
  }),
}));

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: vi.fn().mockReturnValue({
    fetchHistoricalBalanceSeries: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

// Build a raw (camelCased) series response entry as the backend transformer would deliver it.
function entry(opts: { protocol?: string | null; times: number[]; values: string[] }): Record<string, unknown> {
  return {
    asset: 'ETH',
    location: 'ethereum',
    locationLabel: '0xA',
    protocol: opts.protocol ?? null,
    times: opts.times,
    values: opts.values,
  };
}

function success(entries: Record<string, unknown>[], processingRequired = false): unknown {
  return { success: true, result: { entries, processingRequired } };
}

function failure(message: string): unknown {
  return { success: false, message, cancelled: false, backendCancelled: false, skipped: false };
}

describe('useAccountingOverlay', () => {
  let useAccountingOverlay: typeof import('./use-accounting-overlay').useAccountingOverlay;

  beforeEach(async () => {
    vi.useFakeTimers();
    runTaskMock.mockReset();
    ({ useAccountingOverlay } = await import('./use-accounting-overlay'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function create(pairs: OverlayPair[], enabled = true): {
    overlay: ReturnType<typeof useAccountingOverlay>;
    pairsRef: Ref<OverlayPair[]>;
    enabledRef: Ref<boolean>;
  } {
    const pairsRef = ref<OverlayPair[]>(pairs);
    const enabledRef = ref<boolean>(enabled);
    const overlay = useAccountingOverlay({ enabled: enabledRef, pairs: pairsRef });
    return { enabledRef, overlay, pairsRef };
  }

  it('should be disabled and resolve nothing when turned off', () => {
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }], false);
    expect(get(overlay.state)).toBe('disabled');
    expect(overlay.balanceAfter('0xA', 'ETH', 150_000)).toBeUndefined();
  });

  it('should resolve balance_after via step lookup over series points', async () => {
    runTaskMock.mockResolvedValue(success([entry({ times: [100, 200, 300], values: ['1', '3', '2'] })]));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    expect(overlay.statusFor('0xA', 'ETH')).toBe('ready');
    // times are unix seconds; lookups take ms.
    expect(overlay.balanceAfter('0xA', 'ETH', 50_000)?.toString()).toBe('0'); // before first point
    expect(overlay.balanceAfter('0xA', 'ETH', 150_000)?.toString()).toBe('1');
    expect(overlay.balanceAfter('0xA', 'ETH', 250_000)?.toString()).toBe('3');
    expect(overlay.balanceAfter('0xA', 'ETH', 999_000)?.toString()).toBe('2'); // after last point
  });

  it('should sum across wallet and protocol buckets at the same timestamp', async () => {
    runTaskMock.mockResolvedValue(success([
      entry({ protocol: null, times: [100], values: ['5'] }),
      entry({ protocol: 'aave-v3', times: [100], values: ['2'] }),
    ]));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    expect(overlay.balanceAfter('0xA', 'ETH', 150_000)?.toString()).toBe('7');
    const buckets = overlay.bucketsAt('0xA', 'ETH', 150_000);
    expect(buckets).toHaveLength(2);
    expect(buckets.map(b => b.balance.toString())).toEqual(['5', '2']);
    expect(buckets.map(b => b.protocol)).toEqual([null, 'aave-v3']);
  });

  it('should merge same-scope series (null and empty protocol) into one wallet bucket', async () => {
    // Backend splits one plain-wallet position across two consecutive windows, tagging the
    // early one null and the later one '' — they must merge, not double-count.
    runTaskMock.mockResolvedValue(success([
      entry({ protocol: null, times: [100, 200], values: ['10', '4'] }),
      entry({ protocol: '', times: [300, 400], values: ['50', '60'] }),
    ]));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    const buckets = overlay.bucketsAt('0xA', 'ETH', 500_000);
    expect(buckets).toHaveLength(1); // one merged "Wallet" bucket, not two
    expect(buckets[0].protocol).toBeNull();
    // step lookup uses the most recent point of the merged series, no stale-segment addition
    expect(overlay.balanceAfter('0xA', 'ETH', 500_000)?.toString()).toBe('60');
    expect(overlay.balanceAfter('0xA', 'ETH', 250_000)?.toString()).toBe('4');
  });

  it('should mark the pair empty when the backend has no data', async () => {
    runTaskMock.mockResolvedValue(failure('No historical data found'));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    expect(overlay.statusFor('0xA', 'ETH')).toBe('empty');
    expect(overlay.balanceAfter('0xA', 'ETH', 150_000)).toBeUndefined();
  });

  it('should mark the pair processing when metrics are not computed yet', async () => {
    runTaskMock.mockResolvedValue(success([], true));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    expect(overlay.statusFor('0xA', 'ETH')).toBe('processing');
  });

  it('should mark the pair errored on an actionable failure', async () => {
    runTaskMock.mockResolvedValue(failure('boom'));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    expect(overlay.statusFor('0xA', 'ETH')).toBe('error');
  });

  it('should fan out concurrent same-type tasks as non-unique, unguarded', async () => {
    runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['1'] })]));
    const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();

    expect(runTaskMock).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({
        guard: false,
        type: TaskType.QUERY_HISTORICAL_BALANCE_SERIES,
        unique: false,
      }),
    );
  });

  it('should only fetch pairs that are not already cached', async () => {
    runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['1'] })]));
    const { overlay, pairsRef } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
    await overlay.refresh();
    await flushPromises();
    expect(runTaskMock).toHaveBeenCalledTimes(1);

    // adding a new pair fetches only the newcomer; the cached pair is not refetched.
    set(pairsRef, [{ asset: 'ETH', locationLabel: '0xA' }, { asset: 'DAI', locationLabel: '0xA' }]);
    await nextTick();
    await flushPromises();
    expect(runTaskMock).toHaveBeenCalledTimes(2);
  });

  it('should fetch a pair registered via ensurePair that is absent from the view set', async () => {
    // Mirrors a linked asset movement: the deposit pair is not in `groups.data`, so the cell
    // registers it directly. Before registration the cell sees only the loading default.
    runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['9'] })]));
    const { overlay } = create([]);
    await overlay.refresh();
    await flushPromises();
    expect(overlay.statusFor('Crypto.com App', 'CURVE')).toBe('loading');

    overlay.ensurePair({ asset: 'CURVE', locationLabel: 'Crypto.com App' });
    await flushPromises();

    expect(overlay.statusFor('Crypto.com App', 'CURVE')).toBe('ready');
    expect(overlay.balanceAfter('Crypto.com App', 'CURVE', 150_000)?.toString()).toBe('9');
  });

  it('should fetch an ensurePair pair registered before the first refresh', async () => {
    runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['4'] })]));
    const { overlay } = create([]);

    // Registered before init: refresh()'s fetchMissing must pick it up.
    overlay.ensurePair({ asset: 'CURVE', locationLabel: 'Crypto.com App' });
    await overlay.refresh();
    await flushPromises();

    expect(overlay.statusFor('Crypto.com App', 'CURVE')).toBe('ready');
  });

  it('should not refetch a pair already registered via ensurePair', async () => {
    runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['1'] })]));
    const { overlay } = create([]);
    await overlay.refresh();
    await flushPromises();

    overlay.ensurePair({ asset: 'CURVE', locationLabel: 'Crypto.com App' });
    await flushPromises();
    expect(runTaskMock).toHaveBeenCalledTimes(1);

    overlay.ensurePair({ asset: 'CURVE', locationLabel: 'Crypto.com App' });
    await flushPromises();
    expect(runTaskMock).toHaveBeenCalledTimes(1);
  });

  describe('refreshProcessing', () => {
    it('should refetch only the pairs stuck on processing', async () => {
      // 0xA resolves immediately; 0xB is still processing.
      runTaskMock.mockImplementation(async (taskFn: () => Promise<unknown>) => {
        const meta = await taskFn();
        return meta;
      });
      runTaskMock.mockResolvedValueOnce(success([entry({ times: [100], values: ['5'] })])); // 0xA
      runTaskMock.mockResolvedValueOnce(success([], true)); // 0xB processing
      const { overlay } = create([
        { asset: 'ETH', locationLabel: '0xA' },
        { asset: 'ETH', locationLabel: '0xB' },
      ]);
      await overlay.refresh();
      await flushPromises();
      expect(overlay.statusFor('0xA', 'ETH')).toBe('ready');
      expect(overlay.statusFor('0xB', 'ETH')).toBe('processing');
      expect(runTaskMock).toHaveBeenCalledTimes(2);

      // Sync completed: 0xB now has metrics. Only it should be refetched.
      runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['8'] })]));
      overlay.refreshProcessing();
      await flushPromises();

      expect(runTaskMock).toHaveBeenCalledTimes(3); // only 0xB refetched, not the ready 0xA
      expect(overlay.statusFor('0xB', 'ETH')).toBe('ready');
      expect(overlay.balanceAfter('0xB', 'ETH', 150_000)?.toString()).toBe('8');
    });

    it('should do nothing when the overlay is disabled', async () => {
      runTaskMock.mockResolvedValue(success([], true));
      const { overlay, enabledRef } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
      await overlay.refresh();
      await flushPromises();
      expect(runTaskMock).toHaveBeenCalledTimes(1);

      set(enabledRef, false);
      overlay.refreshProcessing();
      await flushPromises();
      expect(runTaskMock).toHaveBeenCalledTimes(1); // guarded: no refetch while disabled
    });
  });

  describe('seriesUpTo', () => {
    it('should return the full balance trajectory up to the event, plus the event point', async () => {
      runTaskMock.mockResolvedValue(success([entry({ times: [100, 200, 300], values: ['1', '3', '2'] })]));
      const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
      await overlay.refresh();
      await flushPromises();

      // event at 400s (ms); no window → all change-points + the held value at the event.
      const series = overlay.seriesUpTo('0xA', 'ETH', 400_000);
      expect(series).toEqual([
        { time: 100, value: 1 },
        { time: 200, value: 3 },
        { time: 300, value: 2 },
        { time: 400, value: 2 },
      ]);
    });

    it('should exclude change-points after the event timestamp', async () => {
      runTaskMock.mockResolvedValue(success([entry({ times: [100, 200, 300], values: ['1', '3', '2'] })]));
      const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
      await overlay.refresh();
      await flushPromises();

      // event at 250s → only points <= 250, plus the event value (3, held since 200).
      const series = overlay.seriesUpTo('0xA', 'ETH', 250_000);
      expect(series).toEqual([
        { time: 100, value: 1 },
        { time: 200, value: 3 },
        { time: 250, value: 3 },
      ]);
    });

    it('should return nothing when the pair is not ready', () => {
      const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
      expect(overlay.seriesUpTo('0xA', 'ETH', 400_000)).toEqual([]);
    });
  });
});
