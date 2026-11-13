import { bigNumberify } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePriceCacheReader } from '@/modules/statistics/pricing/use-price-cache-reader';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

const { queryOnlyCacheHistoricalRates } = vi.hoisted(() => ({
  queryOnlyCacheHistoricalRates: vi.fn(),
}));

vi.mock('@/modules/balances/api/use-price-api', () => ({
  usePriceApi: (): { queryOnlyCacheHistoricalRates: typeof queryOnlyCacheHistoricalRates } => ({ queryOnlyCacheHistoricalRates }),
}));

describe('modules/statistics/pricing/use-price-cache-reader', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    queryOnlyCacheHistoricalRates.mockReset();
  });

  it('should store the cached prices and not ask for the same times again', async () => {
    queryOnlyCacheHistoricalRates.mockResolvedValue({ assets: { USD: { 86400: bigNumberify('0.9') } } });
    const { readCached } = usePriceCacheReader();

    await readCached('USD', [86400]);
    await readCached('USD', [86400]);

    expect(usePriceSeriesStore().prices.USD).toEqual([{ price: bigNumberify('0.9'), time: 86400 }]);
    expect(queryOnlyCacheHistoricalRates).toHaveBeenCalledOnce();
  });

  it('should let a failed read be asked again', async () => {
    queryOnlyCacheHistoricalRates.mockRejectedValueOnce(new Error('backend unreachable'));
    queryOnlyCacheHistoricalRates.mockResolvedValueOnce({ assets: {} });
    const { readCached } = usePriceCacheReader();

    await readCached('USD', [86400]);

    expect(usePriceSeriesStore().isRequested('USD:86400')).toBe(false);
    await readCached('USD', [86400]);
    expect(queryOnlyCacheHistoricalRates).toHaveBeenCalledTimes(2);
  });
});
