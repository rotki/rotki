import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, One } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useSetting } from '@/modules/settings/use-setting';

interface UseHistoricFiatConversionReturn {
  /** Whether the user's display currency is USD (no conversion needed). */
  isUsd: ComputedRef<boolean>;
  /** Whether the historic rate lookup is still in progress. */
  loading: ComputedRef<boolean>;
  /** The USD to display-currency rate at the given timestamp; `One` when the display currency is USD. */
  rate: ComputedRef<BigNumber>;
  /** Whether `rate` is usable (USD, or a positive resolved historic rate). */
  rateReady: ComputedRef<boolean>;
  /**
   * Whether editing is a dead end, because a non-USD value has no historic rate to be stored back
   * as USD with. An editor gates its save on this, since a value stored without the rate silently
   * stops tracking (#12277).
   */
  rateMissing: ComputedRef<boolean>;
  /**
   * {@link rateMissing}, held back until the lookup settles, so the dead-end message does not flash
   * while the historic rate is still being fetched. Message on this; gate the save on `rateMissing`.
   */
  showRateMissing: ComputedRef<boolean>;
}

/**
 * Resolves the historic USD to display-currency rate at a snapshot's timestamp.
 *
 * @remarks
 * Snapshots are stored in USD, so displaying or editing one in another fiat must use the rate that
 * applied *at the snapshot's time*, not today's. Backed by the lazy historic-price cache: reading
 * the rate triggers the fetch, and `loading` reflects the pending state so callers can guard inputs.
 *
 * @param timestamp - the snapshot timestamp in **seconds**, the historic-price cache's key unit;
 * accepts a plain value, a ref or a getter. Never milliseconds.
 */
export function useHistoricFiatConversion(timestamp: MaybeRefOrGetter<number>): UseHistoricFiatConversionReturn {
  const currencySymbol = useSetting('currencySymbol');
  const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();

  const isUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);

  const rate = computed<BigNumber>(() => {
    if (get(isUsd))
      return One;

    return getHistoricPrice(CURRENCY_USD, toValue(timestamp));
  });

  const loading = computed<boolean>(() => {
    if (get(isUsd))
      return false;

    return getIsPending(createKey(CURRENCY_USD, toValue(timestamp)));
  });

  const rateReady = computed<boolean>(() => get(isUsd) || get(rate).isPositive());

  const rateMissing = computed<boolean>(() => !get(isUsd) && !get(rateReady));

  const showRateMissing = computed<boolean>(() => get(rateMissing) && !get(loading));

  watchImmediate([(): number => toValue(timestamp), isUsd], () => {
    if (!get(isUsd))
      getHistoricPrice(CURRENCY_USD, toValue(timestamp));
  });

  return {
    isUsd,
    loading,
    rate,
    rateMissing,
    rateReady,
    showRateMissing,
  };
}
