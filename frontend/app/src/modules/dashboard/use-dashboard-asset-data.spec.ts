import type { DataTableSortData } from '@rotki/ui-library';
import { type AssetBalanceWithPrice, bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDashboardAssetData } from '@/modules/dashboard/use-dashboard-asset-data';

const mockTotalNetWorth = ref(bigNumberify(1000));
const mockMissingCustomAssets = ref<string[]>([]);
const mockAssetInfo = vi.fn((identifier: string | undefined) => ({ name: identifier, symbol: identifier }));

vi.mock('@/modules/dashboard/use-dashboard-stores', () => ({
  useDashboardStores: (): { totalNetWorth: typeof mockTotalNetWorth } => ({ totalNetWorth: mockTotalNetWorth }),
}));

vi.mock('@/modules/assets/use-asset-select-info', () => ({
  useAssetSelectInfo: (): { getAssetInfo: typeof mockAssetInfo } => ({ getAssetInfo: mockAssetInfo }),
}));

vi.mock('@/modules/balances/manual/use-manual-balance-data', () => ({
  useManualBalanceData: (): { missingCustomAssets: typeof mockMissingCustomAssets } => ({ missingCustomAssets: mockMissingCustomAssets }),
}));

function balance(asset: string, value: number): AssetBalanceWithPrice {
  return {
    amount: bigNumberify(value),
    asset,
    price: bigNumberify(1),
    value: bigNumberify(value),
  };
}

const noSort: DataTableSortData<AssetBalanceWithPrice> = [];

describe('useDashboardAssetData', () => {
  beforeEach(() => {
    vi.useRealTimers();
    set(mockTotalNetWorth, bigNumberify(1000));
    set(mockMissingCustomAssets, []);
    mockAssetInfo.mockImplementation((identifier: string | undefined) => ({ name: identifier, symbol: identifier }));
  });

  it('should sum the value of all balances', () => {
    const balances = [balance('BTC', 300), balance('ETH', 200)];
    const { total } = useDashboardAssetData(balances, noSort);
    expect(get(total).toNumber()).toBe(500);
  });

  it('should compute percentage of total net value against net worth', () => {
    const balances = [balance('BTC', 250)];
    const { percentageOfTotalNetValue } = useDashboardAssetData(balances, noSort);
    expect(percentageOfTotalNetValue(balance('BTC', 250))).toBe('25.00');
  });

  it('should fall back to total when net worth is negative', () => {
    set(mockTotalNetWorth, bigNumberify(-1));
    const balances = [balance('BTC', 400)];
    const { percentageOfTotalNetValue } = useDashboardAssetData(balances, noSort);
    expect(percentageOfTotalNetValue(balance('BTC', 100))).toBe('25.00');
  });

  it('should compute percentage of the current group', () => {
    const balances = [balance('BTC', 100), balance('ETH', 300)];
    const { percentageOfCurrentGroup } = useDashboardAssetData(balances, noSort);
    expect(percentageOfCurrentGroup(balance('BTC', 100))).toBe('25.00');
  });

  it('should flag an asset as missing when in the missing custom assets list', () => {
    set(mockMissingCustomAssets, ['CUSTOM']);
    const { isAssetMissing } = useDashboardAssetData([], noSort);
    expect(isAssetMissing(balance('CUSTOM', 1))).toBe(true);
    expect(isAssetMissing(balance('BTC', 1))).toBe(false);
  });

  it('should return all balances sorted when there is no search', () => {
    const balances = [balance('BTC', 100), balance('ETH', 200)];
    const { sorted } = useDashboardAssetData(balances, noSort);
    expect(get(sorted)).toHaveLength(2);
  });

  it('should filter balances by the debounced search keyword', async () => {
    vi.useFakeTimers();
    const balances = [balance('BTC', 100), balance('ETH', 200)];
    const { modelSearch, sorted } = useDashboardAssetData(balances, noSort);

    set(modelSearch, 'BTC');
    await vi.advanceTimersByTimeAsync(200);

    const result = get(sorted);
    expect(result).toHaveLength(1);
    expect(result[0].asset).toBe('BTC');
  });

  it('should react to changes in the balances input', () => {
    const balances = ref<AssetBalanceWithPrice[]>([balance('BTC', 100)]);
    const { total } = useDashboardAssetData(balances, noSort);
    expect(get(total).toNumber()).toBe(100);

    set(balances, [balance('BTC', 100), balance('ETH', 400)]);
    expect(get(total).toNumber()).toBe(500);
  });
});
