import { bigNumberify, type NetValue, NoPrice } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useSnapshotList } from '@/modules/dashboard/snapshots/composables/use-snapshot-list';

const getHistoricPrice = vi.fn();
const getIsPending = vi.fn();
const fetchNetValue = vi.fn();
const netValue = ref<NetValue>({ data: [], times: [] });

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
    getHistoricPrice.mockReturnValue(NoPrice);
    getIsPending.mockReturnValue(false);
    set(netValue, { data: [], times: [] });
  });

  function setCurrency(symbol: string): void {
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency(symbol) });
  }

  it('should pass USD values through unchanged when the display currency is USD', () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(100), bigNumberify(150)], times: [day1, day2] });

    const { rows } = useSnapshotList();
    const result = get(rows);

    expect(result).toHaveLength(2);
    expect(result[0].fiatValue.toNumber()).toBe(100);
    expect(result[0].delta).toBeUndefined();
    expect(result[1].fiatValue.toNumber()).toBe(150);
    expect(result[1].delta?.toNumber()).toBe(50);
    expect(getHistoricPrice).not.toHaveBeenCalled();
  });

  it('should convert each row at its own historic rate for a non-USD currency', () => {
    setCurrency('EUR');
    getHistoricPrice.mockImplementation((_asset: string, ts: number) =>
      ts === day1 ? bigNumberify(0.8) : bigNumberify(0.9));
    set(netValue, { data: [bigNumberify(100), bigNumberify(200)], times: [day1, day2] });

    const { rows } = useSnapshotList();
    const result = get(rows);

    expect(result[0].fiatValue.toNumber()).toBe(80); // 100 * 0.8
    expect(result[1].fiatValue.toNumber()).toBe(180); // 200 * 0.9
    expect(result[1].delta?.toNumber()).toBe(100); // 180 - 80
  });

  it('should mark a row pending and skip its delta while the rate is loading', () => {
    setCurrency('EUR');
    getHistoricPrice.mockImplementation((_asset: string, ts: number) =>
      ts === day2 ? NoPrice : bigNumberify(0.8));
    getIsPending.mockImplementation((key: string) => key === `USD#${day2}`);
    set(netValue, { data: [bigNumberify(100), bigNumberify(200)], times: [day1, day2] });

    const { rows } = useSnapshotList();
    const result = get(rows);

    expect(result[1].fiatPending).toBe(true);
    expect(result[1].ready).toBe(false);
    expect(result[1].fiatValue.toNumber()).toBe(0);
    expect(result[1].delta).toBeUndefined();
  });

  it('should filter by inclusive timestamp range', () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(1), bigNumberify(2), bigNumberify(3)], times: [day1, day2, day3] });

    const { filters, rows } = useSnapshotList();
    set(filters, { fromTimestamp: day2, toTimestamp: day2 });

    const result = get(rows);
    expect(result).toHaveLength(1);
    expect(result[0].timestamp).toBe(day2);
  });

  it('should report whether any snapshot exists regardless of the range filter', () => {
    setCurrency('USD');
    set(netValue, { data: [bigNumberify(1), bigNumberify(2)], times: [day1, day2] });

    const { filters, hasSnapshots, rows } = useSnapshotList();
    // A range that excludes everything still reports snapshots exist.
    set(filters, { fromTimestamp: day3 });

    expect(get(rows)).toHaveLength(0);
    expect(get(hasSnapshots)).toBe(true);
  });

  it('should reflect loading state across a refresh call', async () => {
    setCurrency('USD');
    const { loading, refresh } = useSnapshotList();

    expect(get(loading)).toBe(false);
    await refresh();
    expect(fetchNetValue).toHaveBeenCalledOnce();
    expect(get(loading)).toBe(false);
  });
});
