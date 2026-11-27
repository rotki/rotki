import type { BucketSeries, SeriesRange } from './balance-series';
import { bigNumberify } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type EffectScope, effectScope, ref } from 'vue';
import { AccountHistoryRange, type AccountHistorySelection } from './account-history-selection';
import { useAccountHistory } from './use-account-history';

const state = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    buckets: ref<BucketSeries[]>([]),
    loadedRange: ref<SeriesRange | undefined>(),
    loading: ref<boolean>(false),
    premium: ref<boolean>(true),
    seriesAccount: { read: (): string | undefined => undefined },
    assetsAccount: { read: (): string | undefined => undefined },
    selection: ref<AccountHistorySelection>({ account: undefined, asset: undefined, location: undefined, range: 'all' }),
    seriesError: ref<string | undefined>(),
  };
});

vi.mock('./use-account-history-selection', () => ({
  useAccountHistorySelection: (): Record<string, unknown> => ({
    modelAccount: ref(),
    modelAsset: ref(),
    modelLocation: ref(),
    modelRange: ref(),
    selection: computed(() => state.selection.value),
  }),
}));
vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): typeof state.premium => state.premium,
}));
vi.mock('./use-account-assets', () => ({
  useAccountAssets: (account: () => string | undefined): Record<string, unknown> => {
    state.assetsAccount.read = account;
    return { assets: computed(() => []), error: ref(), loading: ref(false), processingRequired: ref(false) };
  },
}));
vi.mock('./use-account-balance-series', () => ({
  useAccountBalanceSeries: (options: { account: () => string | undefined }): Record<string, unknown> => {
    state.seriesAccount.read = options.account;
    return {
      buckets: computed(() => state.buckets.value),
      error: state.seriesError,
      loadedRange: state.loadedRange,
      loading: state.loading,
      processingRequired: ref(false),
      refresh: vi.fn(),
    };
  },
}));

function bucket(location: string, protocol: string | undefined, values: [number, number][]): BucketSeries {
  return {
    key: `${location}:${protocol ?? ''}`,
    location,
    points: values.map(([time, value]) => ({ time, value: bigNumberify(value) })),
    protocol,
  };
}

let scope: EffectScope;

function create(): ReturnType<typeof useAccountHistory> {
  const result = scope.run(() => useAccountHistory());
  assert(result);
  return result;
}

describe('useAccountHistory', () => {
  beforeEach(() => {
    scope = effectScope();
    set(state.selection, { account: '0xA', asset: 'ETH', location: undefined, range: AccountHistoryRange.ALL });
    set(state.buckets, [
      bucket('ethereum', undefined, [[100, 2], [300, 2]]),
      bucket('optimism', undefined, [[200, 3], [300, 3]]),
    ]);
    set(state.loadedRange, { from: 0, to: 300 });
    set(state.loading, false);
    set(state.seriesError, undefined);
    set(state.premium, true);
  });

  afterEach(() => scope.stop());

  it('should offer every location the asset is held in and total them all', () => {
    const { locations, summary } = create();

    expect(get(locations)).toEqual(['ethereum', 'optimism']);
    expect(get(summary).current.toString()).toBe('5');
  });

  it('should narrow the chart and total to the picked location', () => {
    set(state.selection, { ...get(state.selection), location: 'optimism' });
    const { buckets, locations, summary } = create();

    expect(get(buckets).map(({ location }) => location)).toEqual(['optimism']);
    expect(get(summary).current.toString()).toBe('3');
    expect(get(locations)).toEqual(['ethereum', 'optimism']);
  });

  it('should be empty once a loaded pick held nothing', () => {
    set(state.buckets, []);
    const { empty } = create();

    expect(get(empty)).toBe(true);
  });

  it('should not read as empty while nothing is loaded, loading or failed', () => {
    set(state.buckets, []);
    const { empty } = create();

    set(state.loading, true);
    expect(get(empty)).toBe(false);

    set(state.loading, false);
    set(state.seriesError, 'boom');
    expect(get(empty)).toBe(false);

    set(state.seriesError, undefined);
    set(state.loadedRange, undefined);
    expect(get(empty)).toBe(false);
  });

  it('should ask the balance endpoints about the account only with premium', () => {
    create();
    expect(state.seriesAccount.read()).toBe('0xA');
    expect(state.assetsAccount.read()).toBe('0xA');

    set(state.premium, false);

    expect(state.seriesAccount.read()).toBeUndefined();
    expect(state.assetsAccount.read()).toBeUndefined();
  });

  it('should give the events the loaded range with premium, and the picked range from now without it', () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-11-27T00:00:00Z'));
    set(state.selection, { ...get(state.selection), range: AccountHistoryRange.MONTH });
    const { eventsRange } = create();
    expect(get(eventsRange)).toEqual({ from: 0, to: 300 });

    set(state.premium, false);

    expect(get(eventsRange)).toEqual({
      from: new Date('2026-10-27T00:00:00Z').getTime() / 1000,
      to: new Date('2026-11-27T00:00:00Z').getTime() / 1000,
    });
    vi.useRealTimers();
  });
});
