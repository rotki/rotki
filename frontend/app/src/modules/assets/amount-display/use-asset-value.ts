import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { Timestamp } from '@/modules/assets/amount-display/types';
import { type BigNumber, Zero } from '@rotki/common';
import { useHistoricRate } from '@/modules/assets/amount-display/use-historic-rate';
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

/** Treats a zero, negative or missing price as no price at all. */
function positiveOrZero(value: BigNumber): BigNumber {
  return value.gt(0) ? value : Zero;
}

/**
 * Calculates the value of an asset in the user's currency, from an amount and a price.
 *
 * @remarks
 * The price comes from one of three sources, in order: the historic price at a given timestamp,
 * a price the caller already knows, or the current price from the cache.
 *
 * A timestamped lookup never falls back to the current price. Showing today's price against a
 * historic date reads as a real figure while being wrong by however much the price has moved,
 * whereas a zero reads as missing.
 */
export function useAssetValue(options: UseAssetValueOptions): UseAssetValueReturn {
  const {
    amount,
    asset,
    knownPrice,
    timestamp,
  } = options;

  const { getAssetPrice } = usePriceUtils();
  const { isHistoric, loading, rate: historicPrice } = useHistoricRate(asset, timestamp);

  const price = computed<BigNumber>(() => {
    const assetVal = toValue(asset);
    const known = toValue(knownPrice);

    if (!assetVal)
      return Zero;

    if (get(isHistoric))
      return positiveOrZero(get(historicPrice));

    if (known !== undefined && known !== null)
      return positiveOrZero(known);

    return positiveOrZero(getAssetPrice(assetVal, Zero));
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
