import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';
import { normalizeTimestamp, type Timestamp } from '@/modules/assets/amount-display/types';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';

export interface UseAssetValueOptions {
  /** Asset identifier to price */
  asset: MaybeRefOrGetter<string>;
  /** Amount of the asset */
  amount: MaybeRefOrGetter<BigNumber>;
  /** Known price (optional, will look up if not provided) */
  knownPrice?: MaybeRefOrGetter<BigNumber | null | undefined>;
  /** Timestamp for historic price lookup */
  timestamp?: MaybeRefOrGetter<Timestamp | undefined>;
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

  const { getAssetPrice } = usePriceUtils();
  const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();

  const timestampToUse = computed<number>(() => {
    const ts = normalizeTimestamp(toValue(timestamp));
    if (ts === undefined || ts <= 0) {
      return -1;
    }
    return ts;
  });

  const loading = computed<boolean>(() => {
    const assetVal = toValue(asset);
    const ts = get(timestampToUse);

    if (!assetVal) {
      return false;
    }

    if (ts > 0) {
      return getIsPending(createKey(assetVal, ts));
    }

    return false;
  });

  const price = computed<BigNumber>(() => {
    const assetVal = toValue(asset);
    const ts = get(timestampToUse);
    const known = toValue(knownPrice);

    if (!assetVal) {
      return Zero;
    }

    // If historic timestamp is provided, use historic price (no fallback to current price)
    if (ts > 0) {
      const historicPrice = getHistoricPrice(assetVal, ts);
      if (historicPrice.gt(0)) {
        return historicPrice;
      }
      return Zero;
    }

    // If known price is provided, use it directly
    if (known !== undefined && known !== null) {
      return known.gt(0) ? known : Zero;
    }

    // Fall back to looking up the price (already in current currency)
    const current = getAssetPrice(assetVal, Zero);
    return current.gt(0) ? current : Zero;
  });

  const value = computed<BigNumber>(() => {
    const amountVal = toValue(amount);
    const priceVal = get(price);

    if (amountVal.isZero() || priceVal.lte(0)) {
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
