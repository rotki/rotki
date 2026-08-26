import { bigNumberify, type NetValue } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';

const getHistoricPrice = vi.fn();
const getIsPending = vi.fn();
const fetchNetValue = vi.fn();
const netValue = ref<NetValue>({ data: [], times: [] });

// The historic-price cache is mocked purely as a regression guard: the list
// derivation must stay pure (USD-only) so it never hammers the forex endpoint.
// If eager conversion is ever reintroduced, these spies would be called and the
// "does not touch the historic-price cache" assertions would fail.
vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: vi.fn(() => ({
    createKey: (fromAsset: string, timestamp: number): string => `${fromAsset}#${timestamp}`,
    getHistoricPrice,
    getIsPending,
  })),
}));

vi.mock('@/modules/statistics/use-statistics-store', () => ({
  useStatisticsStore: vi.fn(() => ({ netValue })),
}));

vi.mock('@/modules/statistics/use-statistics-data-fetching', () => ({
  useStatisticsDataFetching: vi.fn(() => ({ fetchNetValue })),
}));

describe('modules/dashboard/snapshots/composables/use-snapshot-list', () => {
  // Snapshot timestamps are in seconds, matching the historic-price cache key.
  const day1 = 1_600_000_000;
  const day2 = 1_600_086_400;
  const day3 = 1_600_172_800;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(netValue, { data: [], times: [] });
  });

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  it('should expose the stored USD value for each snapshot', () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(100), bigNumberify(150)], times: [day1, day2] });

    const { rows } = withSetup(() => useSnapshotList()).result;
    const result = get(rows);

    expect(result).toHaveLength(2);
    expect(result[0].timestamp).toBe(day1);
    expect(result[0].usdValue.toNumber()).toBe(100);
    expect(result[1].timestamp).toBe(day2);
    expect(result[1].usdValue.toNumber()).toBe(150);
  });

  it('should attach the chronological predecessor for the delta', () => {
    setCurrency('EUR');
    set(netValue, { data: [bigNumberify(100), bigNumberify(200), bigNumberify(250)], times: [day1, day2, day3] });

    const { rows } = withSetup(() => useSnapshotList()).result;
    const result = get(rows);

    // The oldest snapshot has no predecessor.
    expect(result[0].previousTimestamp).toBeUndefined();
    expect(result[0].previousUsdValue).toBeUndefined();
    // Every later row points at the immediately preceding snapshot.
    expect(result[1].previousTimestamp).toBe(day1);
    expect(result[1].previousUsdValue?.toNumber()).toBe(100);
    expect(result[2].previousTimestamp).toBe(day2);
    expect(result[2].previousUsdValue?.toNumber()).toBe(200);
  });

  it('should never touch the historic-price cache, even for a large series', () => {
    setCurrency('EUR');
    const size = 3000;
    const data = Array.from({ length: size }, (_, i) => bigNumberify(i + 1));
    const times = Array.from({ length: size }, (_, i) => day1 + i * 86_400);
    set(netValue, { data, times });

    const { rows } = withSetup(() => useSnapshotList()).result;

    // The derivation is pure: reading every row triggers no forex lookups.
    expect(get(rows)).toHaveLength(size);
    expect(getHistoricPrice).not.toHaveBeenCalled();
    expect(getIsPending).not.toHaveBeenCalled();
  });

  it('should filter by inclusive timestamp range', () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(1), bigNumberify(2), bigNumberify(3)], times: [day1, day2, day3] });

    const { filters, rows } = withSetup(() => useSnapshotList()).result;
    set(filters, { fromTimestamp: day2, toTimestamp: day2 });

    const result = get(rows);
    expect(result).toHaveLength(1);
    expect(result[0].timestamp).toBe(day2);
  });

  it('should keep the full-series predecessor on a row excluded by the filter', () => {
    setCurrency('EUR');
    set(netValue, { data: [bigNumberify(100), bigNumberify(200), bigNumberify(300)], times: [day1, day2, day3] });

    const { filters, rows } = withSetup(() => useSnapshotList()).result;
    // Exclude day1, so day2 becomes the first visible row but keeps its day1 predecessor.
    set(filters, { fromTimestamp: day2 });

    const result = get(rows);
    expect(result[0].timestamp).toBe(day2);
    expect(result[0].previousTimestamp).toBe(day1);
    expect(result[0].previousUsdValue?.toNumber()).toBe(100);
  });

  it('should report whether any snapshot exists regardless of the range filter', () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(1), bigNumberify(2)], times: [day1, day2] });

    const { filters, hasSnapshots, rows } = withSetup(() => useSnapshotList()).result;
    // A range that excludes everything still reports snapshots exist.
    set(filters, { fromTimestamp: day3 });

    expect(get(rows)).toHaveLength(0);
    expect(get(hasSnapshots)).toBe(true);
  });

  it('should fetch on mount when the series is empty', async () => {
    setCurrency('USD');
    withSetup(() => useSnapshotList());
    await flushPromises();

    expect(fetchNetValue).toHaveBeenCalledOnce();
  });

  it('should not fetch on mount when the series is already loaded', async () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(100), bigNumberify(150)], times: [day1, day2] });

    withSetup(() => useSnapshotList());
    await flushPromises();

    expect(fetchNetValue).not.toHaveBeenCalled();
  });

  it('should reflect loading state across a refresh call', async () => {
    setCurrency('USD');
    const { loading, refresh } = withSetup(() => useSnapshotList()).result;
    // netValue is empty at mount, so onMounted fires an initial refresh; let it
    // settle and ignore it so the assertions target the explicit refresh below.
    await flushPromises();
    fetchNetValue.mockClear();

    expect(get(loading)).toBe(false);
    await refresh();
    expect(fetchNetValue).toHaveBeenCalledOnce();
    expect(get(loading)).toBe(false);
  });
});
