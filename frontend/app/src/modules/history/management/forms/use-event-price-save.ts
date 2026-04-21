import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface UseEventPriceSaveReturn {
  savePrice: (fromAsset: string, toAsset: string, price: string, timestampMs: number) => Promise<void>;
}

export function useEventPriceSave(): UseEventPriceSaveReturn {
  const { addHistoricalPrice } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricPriceCache();

  async function savePrice(fromAsset: string, toAsset: string, price: string, timestampMs: number): Promise<void> {
    const payload: HistoricalPriceFormPayload = {
      fromAsset,
      price,
      sourceType: PriceOracle.MANUAL,
      timestamp: millisecondsToSeconds(timestampMs),
      toAsset,
    };
    await addHistoricalPrice(payload);
    resetHistoricalPricesData([payload]);
  }

  return { savePrice };
}
