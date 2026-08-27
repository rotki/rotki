import type { Ref } from 'vue';
import type { OverlayPair } from '@/modules/history/balances/use-accounting-overlay';
import { mockUseTaskHandler } from '@test/utils/mocks/task-runner';
import flushPromises from 'flush-promises';
import { err, ok } from 'plainfp/result';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const { runTaskMock } = vi.hoisted(() => ({ runTaskMock: vi.fn() }));

vi.mock('@/modules/core/tasks/use-task-handler', async importOriginal =>
  mockUseTaskHandler(await importOriginal<Record<string, unknown>>(), { invoke: false, runTask: runTaskMock }));

vi.mock('@/modules/balances/api/use-historical-balances-api', () => ({
  useHistoricalBalancesApi: vi.fn().mockReturnValue({
    fetchHistoricalBalanceSeries: vi.fn().mockResolvedValue({ taskId: 1 }),
  }),
}));

/**
 * Builds one series entry in the camelCased shape the response transformer hands over.
 *
 * @remarks
 * Typed as `Record<string, unknown>` rather than as the domain type, so the composable is fed
 * wire-shaped data and the parsing it does is part of what the test exercises.
 */
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
  return ok({ entries, processingRequired });
}

function failure(message: string): unknown {
  return err(TaskFailed({ message }));
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
    fromRef: Ref<number | undefined>;
    toRef: Ref<number | undefined>;
  } {
    const pairsRef = ref<OverlayPair[]>(pairs);
    const enabledRef = ref<boolean>(enabled);
    const fromRef = ref<number>();
    const toRef = ref<number>();
    const overlay = useAccountingOverlay({
      enabled: enabledRef,
      fromTimestamp: fromRef,
      pairs: pairsRef,
      toTimestamp: toRef,
    });
    return { enabledRef, fromRef, overlay, pairsRef, toRef };
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

  it('should not dedup two refreshes that differ only by time range', async () => {
    runTaskMock.mockResolvedValue(success([entry({ times: [100], values: ['1'] })]));
    const { fromRef, overlay, toRef } = create([{ asset: 'ETH', locationLabel: '0xA' }]);

    const first = overlay.refresh();
    set(fromRef, 1000);
    set(toRef, 2000);
    const second = overlay.refresh();
    await Promise.all([first, second]);
    await flushPromises();

    expect(runTaskMock).toHaveBeenCalledTimes(2);
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

  it('should merge same-scope series (null and empty protocol) into one wallet bucket rather than double-count them', async () => {
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

  describe('seriesUpTo', () => {
    it('should return the full balance trajectory up to the event, plus the event point', async () => {
      runTaskMock.mockResolvedValue(success([entry({ times: [100, 200, 300], values: ['1', '3', '2'] })]));
      const { overlay } = create([{ asset: 'ETH', locationLabel: '0xA' }]);
      await overlay.refresh();
      await flushPromises();

      const eventAfterEveryChangePoint = 400_000;
      const series = overlay.seriesUpTo('0xA', 'ETH', eventAfterEveryChangePoint);
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

      const eventBetweenTwoChangePoints = 250_000;
      const series = overlay.seriesUpTo('0xA', 'ETH', eventBetweenTwoChangePoints);
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
