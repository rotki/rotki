import { type BigNumber, bigNumberify, One } from '@rotki/common';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type Ref, ref } from 'vue';
import { useCurrencies } from '@/modules/assets/amount-display/currencies';
import { useSnapshotFxOverride } from '@/modules/dashboard/snapshots/composables/use-snapshot-fx-override';

const TS = 1_600_000_000;

const addHistoricalPrice = vi.fn(async (): Promise<boolean> => true);
const editHistoricalPrice = vi.fn(async (): Promise<boolean> => true);
const deleteHistoricalPrice = vi.fn(async (): Promise<boolean> => true);
const fetchHistoricalPrices = vi.fn(async (): Promise<{ timestamp: number; price: BigNumber }[]> => []);
const resetHistoricalPricesData = vi.fn();

vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): Record<string, unknown> => ({
    addHistoricalPrice,
    deleteHistoricalPrice,
    editHistoricalPrice,
    fetchHistoricalPrices,
  }),
}));

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({ resetHistoricalPricesData }),
}));

const isUsd = ref<boolean>(false);
const rate = ref<BigNumber>(One);
const rateReady = ref<boolean>(true);

vi.mock('@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion', () => ({
  useHistoricFiatConversion: (): { isUsd: Ref<boolean>; loading: Ref<boolean>; rate: Ref<BigNumber>; rateReady: Ref<boolean> } => ({
    isUsd,
    loading: ref(false),
    rate,
    rateReady,
  }),
}));

describe('modules/dashboard/snapshots/composables/use-snapshot-fx-override', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    const { findCurrency } = useCurrencies();
    updateGeneralSettings({ mainCurrency: findCurrency('EUR') });
    set(isUsd, false);
    set(rateReady, true);
    addHistoricalPrice.mockClear();
    editHistoricalPrice.mockClear();
    deleteHistoricalPrice.mockClear();
    fetchHistoricalPrices.mockClear();
    resetHistoricalPricesData.mockClear();
  });

  it('should add a manual price and bust the cache when no override exists', async () => {
    const { setOverride } = useSnapshotFxOverride(TS);

    const success = await setOverride(bigNumberify(0.92));

    expect(success).toBe(true);
    expect(addHistoricalPrice).toHaveBeenCalledWith({
      fromAsset: 'USD',
      price: '0.92',
      sourceType: 'manual',
      timestamp: TS,
      toAsset: 'EUR',
    });
    expect(editHistoricalPrice).not.toHaveBeenCalled();
    expect(resetHistoricalPricesData).toHaveBeenCalledWith([{ fromAsset: 'USD', timestamp: TS }]);
  });

  it('should edit the manual price when an override already exists', async () => {
    fetchHistoricalPrices.mockResolvedValueOnce([{ price: bigNumberify(0.9), timestamp: TS }]);
    const { refreshOverride, setOverride } = useSnapshotFxOverride(TS);
    await refreshOverride();

    await setOverride(bigNumberify(0.95));

    expect(editHistoricalPrice).toHaveBeenCalledTimes(1);
    expect(addHistoricalPrice).not.toHaveBeenCalled();
  });

  it('should resolve the current override from the fetched prices at the timestamp', async () => {
    fetchHistoricalPrices.mockResolvedValueOnce([
      { price: bigNumberify(0.8), timestamp: TS - 99 },
      { price: bigNumberify(0.91), timestamp: TS },
    ]);
    const { currentOverride, refreshOverride } = useSnapshotFxOverride(TS);

    await refreshOverride();

    expect(get(currentOverride)?.toNumber()).toBe(0.91);
  });

  it('should not fetch or expose an override when the display currency is USD', async () => {
    set(isUsd, true);
    const { currentOverride, refreshOverride } = useSnapshotFxOverride(TS);

    await refreshOverride();

    expect(fetchHistoricalPrices).not.toHaveBeenCalled();
    expect(get(currentOverride)).toBeUndefined();
  });

  it('should delete the manual price on clearOverride', async () => {
    fetchHistoricalPrices.mockResolvedValueOnce([{ price: bigNumberify(0.9), timestamp: TS }]);
    const { clearOverride, refreshOverride } = useSnapshotFxOverride(TS);
    await refreshOverride();

    const success = await clearOverride();

    expect(success).toBe(true);
    expect(deleteHistoricalPrice).toHaveBeenCalledWith({
      fromAsset: 'USD',
      sourceType: 'manual',
      timestamp: TS,
      toAsset: 'EUR',
    });
    expect(resetHistoricalPricesData).toHaveBeenCalled();
  });

  it('should not call the delete endpoint when there is no override to clear', async () => {
    const { clearOverride } = useSnapshotFxOverride(TS);

    const success = await clearOverride();

    expect(success).toBe(false);
    expect(deleteHistoricalPrice).not.toHaveBeenCalled();
  });
});
