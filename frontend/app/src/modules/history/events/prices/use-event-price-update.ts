import type { HistoricalPriceFormPayload, OraclePriceEntry } from '@/modules/assets/prices/price-types';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { millisecondsToSeconds } from '@/modules/core/common/data/date';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

export type EventPriceUpdateMode = 'oracle' | 'manual';

export interface EventPriceUpdateParams {
  fromAsset: string;
  toAsset: string;
  price: string;
  timestampMs: number;
  mode: EventPriceUpdateMode;
  existingEntry?: OraclePriceEntry;
}

interface UseEventPriceUpdateReturn {
  fetchExistingEntry: (fromAsset: string, toAsset: string, timestampMs: number) => Promise<OraclePriceEntry | undefined>;
  updatePrice: (params: EventPriceUpdateParams) => Promise<void>;
}

export function useEventPriceUpdate(): UseEventPriceUpdateReturn {
  const { addHistoricalPrice, editHistoricalPrice, fetchOraclePrices } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricPriceCache();

  async function fetchExistingEntry(
    fromAsset: string,
    toAsset: string,
    timestampMs: number,
  ): Promise<OraclePriceEntry | undefined> {
    const timestamp = millisecondsToSeconds(timestampMs);
    const collection = await fetchOraclePrices({
      fromAsset,
      fromTimestamp: timestamp,
      limit: 1,
      offset: 0,
      toAsset,
      toTimestamp: timestamp,
    });
    return collection.data[0];
  }

  async function updatePrice(params: EventPriceUpdateParams): Promise<void> {
    const { existingEntry, fromAsset, mode, price, timestampMs, toAsset } = params;
    const timestamp = millisecondsToSeconds(timestampMs);

    const useEdit = mode === 'oracle'
      ? Boolean(existingEntry)
      : existingEntry?.sourceType === PriceOracle.MANUAL;

    const sourceType = mode === 'oracle' && existingEntry
      ? existingEntry.sourceType
      : PriceOracle.MANUAL;

    const payload: HistoricalPriceFormPayload = {
      fromAsset,
      price,
      sourceType,
      timestamp,
      toAsset,
    };

    if (useEdit)
      await editHistoricalPrice(payload);
    else
      await addHistoricalPrice(payload);

    resetHistoricalPricesData([payload]);
  }

  return {
    fetchExistingEntry,
    updatePrice,
  };
}
