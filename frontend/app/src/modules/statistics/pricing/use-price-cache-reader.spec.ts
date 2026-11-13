import { bigNumberify } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { defaultGeneralSettings } from '@/modules/settings/factories';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { usePriceCacheReader } from '@/modules/statistics/pricing/use-price-cache-reader';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';

const { queryOnlyCacheHistoricalRates } = vi.hoisted(() => ({
  queryOnlyCacheHistoricalRates: vi.fn(),
}));

vi.mock('@/modules/balances/api/use-price-api', () => ({
  usePriceApi: (): { queryOnlyCacheHistoricalRates: typeof queryOnlyCacheHistoricalRates } => ({ queryOnlyCacheHistoricalRates }),
}));

function setMainCurrency(symbol: string): void {
  const { findCurrency } = useCurrencies();
  useSettingsRepo().updateGeneral({ ...defaultGeneralSettings(findCurrency(symbol)), mainCurrency: findCurrency(symbol) });
}

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
    queryOnlyCacheHistoricalRates.mockResolvedValue({ assets: {} });
    const { readCached } = usePriceCacheReader();

    await readCached('USD', [86400]);

    expect(usePriceSeriesStore().isRequested('USD:86400')).toBe(false);
    await readCached('USD', [86400]);
    expect(queryOnlyCacheHistoricalRates).toHaveBeenNthCalledWith(2, expect.objectContaining({ assetsTimestamp: [['USD', '86400']] }));
  });

  it('should invert the main currency\'s own price when the direct rate is not cached', async () => {
    setMainCurrency('ETH');
    queryOnlyCacheHistoricalRates.mockResolvedValueOnce({ assets: {} });
    queryOnlyCacheHistoricalRates.mockResolvedValueOnce({ assets: { ETH: { 86400: bigNumberify('2000') } } });
    const { readCached } = usePriceCacheReader();

    await readCached('USD', [86400]);

    expect(queryOnlyCacheHistoricalRates).toHaveBeenNthCalledWith(1, expect.objectContaining({ assetsTimestamp: [['USD', '86400']], targetAsset: 'ETH' }));
    expect(queryOnlyCacheHistoricalRates).toHaveBeenNthCalledWith(2, expect.objectContaining({ assetsTimestamp: [['ETH', '86400']], targetAsset: 'USD' }));
    expect(usePriceSeriesStore().prices.USD?.map(point => point.price.toFixed())).toEqual(['0.0005']);
  });
});
