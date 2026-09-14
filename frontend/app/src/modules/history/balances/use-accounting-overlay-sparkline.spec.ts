import type { EffectScope, Ref } from 'vue';
import type { PreparedBucket } from './accounting-overlay-helpers';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingOverlaySparkline } from './use-accounting-overlay-sparkline';

const seriesFor = vi.fn<(locationLabel: string, asset: string) => Promise<PreparedBucket[] | undefined>>();

const event = createMock<HistoryEventEntry>({ asset: 'ETH', identifier: 1, locationLabel: '0xA', timestamp: 250_000 });

function series(): PreparedBucket[] {
  return [{
    location: 'ethereum',
    protocol: null,
    times: [100, 200, 300],
    values: [bigNumberify('5'), bigNumberify('7'), bigNumberify('9')],
  }];
}

let scope: EffectScope;

function create(
  enabled: Ref<boolean>,
  balance: Ref<BigNumber>,
  entry: () => HistoryEventEntry = (): HistoryEventEntry => event,
): ReturnType<typeof useAccountingOverlaySparkline> {
  const sparkline = scope.run(() => useAccountingOverlaySparkline(entry, balance, { enabled, seriesFor }));
  assert(sparkline);
  return sparkline;
}

describe('useAccountingOverlaySparkline', () => {
  beforeEach(() => {
    scope = effectScope();
    seriesFor.mockReset().mockResolvedValue(series());
  });

  afterEach(() => scope.stop());

  it('should end the shared series on the exact snapshot rather than the series value', async () => {
    const { points } = create(ref<boolean>(true), ref<BigNumber>(bigNumberify('0')));
    await flushPromises();

    expect(seriesFor).toHaveBeenCalledExactlyOnceWith('0xA', 'ETH');
    expect(get(points)).toEqual([{ time: 100, value: 5 }, { time: 200, value: 7 }, { time: 250, value: 0 }]);
  });

  it('should not request the series while the chart is not allowed', async () => {
    const enabled = ref<boolean>(false);
    const { points } = create(enabled, ref<BigNumber>(bigNumberify('0')));
    await flushPromises();
    expect(seriesFor).not.toHaveBeenCalled();
    expect(get(points)).toEqual([]);

    set(enabled, true);
    await flushPromises();
    expect(seriesFor).toHaveBeenCalledOnce();
  });

  it('should report loading until the series arrives', async () => {
    let resolveSeries: (buckets: PreparedBucket[]) => void = () => {};
    seriesFor.mockReturnValueOnce(new Promise<PreparedBucket[]>((resolve) => {
      resolveSeries = resolve;
    }));
    const { loading } = create(ref<boolean>(true), ref<BigNumber>(bigNumberify('0')));
    await flushPromises();
    expect(get(loading)).toBe(true);

    resolveSeries(series());
    await flushPromises();
    expect(get(loading)).toBe(false);
  });

  it('should drop a series that arrives after the event moved to another asset', async () => {
    let resolveEth: (buckets: PreparedBucket[]) => void = () => {};
    seriesFor.mockImplementation(async (_locationLabel, asset) => {
      if (asset !== 'ETH')
        return [{ location: 'ethereum', protocol: null, times: [100, 200], values: [bigNumberify('2'), bigNumberify('2')] }];
      return new Promise<PreparedBucket[]>((resolve) => {
        resolveEth = resolve;
      });
    });
    const current = shallowRef<HistoryEventEntry>(event);
    const { points } = create(ref<boolean>(true), ref<BigNumber>(bigNumberify('0')), () => get(current));
    await flushPromises();

    set(current, createMock<HistoryEventEntry>({ asset: 'DAI', identifier: 2, locationLabel: '0xA', timestamp: 250_000 }));
    await flushPromises();
    resolveEth(series());
    await flushPromises();

    expect(seriesFor.mock.calls.map(([, asset]) => asset)).toEqual(['ETH', 'DAI']);
    expect(get(points).map(point => point.value)).toEqual([2, 2, 0]);
  });

  it('should move the endpoint with a refreshed snapshot without refetching', async () => {
    const balance = ref<BigNumber>(bigNumberify('0'));
    const { points } = create(ref<boolean>(true), balance);
    await flushPromises();

    set(balance, bigNumberify('4'));
    expect(get(points).at(-1)).toEqual({ time: 250, value: 4 });
    expect(seriesFor).toHaveBeenCalledOnce();
  });
});
