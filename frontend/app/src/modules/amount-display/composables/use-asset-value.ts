import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';
import { normalizeTimestamp, type Timestamp } from '@/modules/amount-display/types';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useHistoricCachePriceStore } from '@/store/prices/historic';

export interface UseAssetValueOptions {
  /** Asset identifier to price */
  asset: MaybeRef<string>;
  /** Amount of the asset */
  amount: MaybeRef<BigNumber>;
  /** Known price (optional, will look up if not provided) */
  knownPrice?: MaybeRef<BigNumber | null | undefined>;
  /** Timestamp for historic price lookup */
  timestamp?: MaybeRef<Timestamp | undefined>;
}

export interface UseAssetValueReturn {
  /** The calculated value in user's currency (amount × price) */
  value: ComputedRef<BigNumber>;
  /** The price per unit of the asset */
  price: ComputedRef<BigNumber>;
  /** Whether price lookup is in progress */
  loading: ComputedRef<boolean>;
}

/**
 * Calculates the value of an asset in the user's currency based on amount and price.
 *
 * Handles:
 * - Using a known price when provided
 * - Looking up current prices from cache
 * - Looking up historic prices when timestamp is provided
 */
export function useAssetValue(options: UseAssetValueOptions): UseAssetValueReturn {
  const {
    amount,
    asset,
    knownPrice,
    timestamp,
  } = options;

  const { assetPrice, isAssetPriceInCurrentCurrency } = usePriceUtils();
  const { createKey, historicPriceInCurrentCurrency, isPending } = useHistoricCachePriceStore();

  // Check if the asset's price is already in the user's current currency
  const isCurrentCurrency = isAssetPriceInCurrentCurrency(asset);

  const timestampToUse = computed<number>(() => {
    const ts = normalizeTimestamp(get(timestamp));
    if (ts === undefined || ts <= 0) {
      return -1;
    }
    return ts;
  });

  const loading = computed<boolean>(() => {
    const assetVal = get(asset);
    const ts = get(timestampToUse);

    if (!assetVal) {
      return false;
    }

    if (ts > 0) {
      return get(isPending(createKey(assetVal, ts)));
    }

    return false;
  });

  const price = computed<BigNumber>(() => {
    const assetVal = get(asset);
    const ts = get(timestampToUse);
    const known = get(knownPrice);

    if (!assetVal) {
      return Zero;
    }

    // If historic timestamp is provided, use historic price
    if (ts > 0) {
      const historicPrice = get(historicPriceInCurrentCurrency(assetVal, ts));
      if (historicPrice.gt(0)) {
        return historicPrice;
      }
    }

    // If known price is provided and price is in current currency, use known price
    if (known !== undefined && known !== null && get(isCurrentCurrency)) {
      return known;
    }

    // Fall back to looking up the price (already in current currency)
    return get(assetPrice(asset)) ?? Zero;
  });

  const value = computed<BigNumber>(() => {
    const amountVal = get(amount);
    const priceVal = get(price);

    if (amountVal.isZero() || priceVal.isZero()) {
      return Zero;
    }

    return amountVal.multipliedBy(priceVal);
  });

  return {
    loading,
    price,
    value,
  };
}
