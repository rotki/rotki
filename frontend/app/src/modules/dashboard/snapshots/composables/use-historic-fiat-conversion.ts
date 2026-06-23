import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, One } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

interface UseHistoricFiatConversionReturn {
  /** Whether the user's display currency is USD (no conversion needed). */
  isUsd: ComputedRef<boolean>;
  /** Whether the historic rate lookup is still in progress. */
  loading: ComputedRef<boolean>;
  /** The USD -> display-currency rate at the given timestamp (One when USD). */
  rate: ComputedRef<BigNumber>;
  /** Whether `rate` is usable (USD, or a positive resolved historic rate). */
  rateReady: ComputedRef<boolean>;
}

/**
 * Resolves the historic USD -> display-currency rate at a snapshot's
 * timestamp (#12277). Snapshots are stored in USD; displaying or editing them
 * in the user's fiat must use the rate that applied *at the snapshot's time*,
 * not today's exchange rate.
 *
 * Backed by the lazy historic-price cache: accessing the rate triggers the
 * fetch and `loading` reflects the pending state so callers can guard inputs.
 *
 * @param timestamp the snapshot timestamp in SECONDS (the historic-price cache
 *   key unit) — plain value, ref or getter. Do not pass milliseconds.
 */
export function useHistoricFiatConversion(timestamp: MaybeRefOrGetter<number>): UseHistoricFiatConversionReturn {
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
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

  // Eagerly kick the lazy historic-rate fetch on mount and whenever the
  // timestamp changes. `resolve()` marks the key pending synchronously, so this
  // makes `loading` true before the first paint — without it, consumers briefly
  // render a not-yet-fetched rate as "no rate" (the #12277 dead-end) during
  // navigation, before the fetch registers as pending.
  watchImmediate([(): number => toValue(timestamp), isUsd], () => {
    if (!get(isUsd))
      getHistoricPrice(CURRENCY_USD, toValue(timestamp));
  });

  return {
    isUsd,
    loading,
    rate,
    rateReady,
  };
}
