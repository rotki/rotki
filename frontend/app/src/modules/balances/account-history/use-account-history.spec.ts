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
vi.mock('./use-account-assets', () => ({
  useAccountAssets: (): Record<string, unknown> => ({ assets: computed(() => []), error: ref(), loading: ref(false), processingRequired: ref(false) }),
}));
vi.mock('./use-account-balance-series', () => ({
  useAccountBalanceSeries: (): Record<string, unknown> => ({
    buckets: computed(() => state.buckets.value),
    error: state.seriesError,
    loadedRange: state.loadedRange,
    loading: state.loading,
    processingRequired: ref(false),
    refresh: vi.fn(),
  }),
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

  it('should not read as empty while nothing is picked, loading or failed', () => {
    set(state.buckets, []);
    const { empty } = create();

    set(state.loading, true);
    expect(get(empty)).toBe(false);

    set(state.loading, false);
    set(state.seriesError, 'boom');
    expect(get(empty)).toBe(false);

    set(state.seriesError, undefined);
    set(state.selection, { ...get(state.selection), asset: undefined });
    expect(get(empty)).toBe(false);
  });
});
