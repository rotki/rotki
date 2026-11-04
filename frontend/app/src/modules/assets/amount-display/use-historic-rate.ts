import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';
import { normalizeTimestamp, type Timestamp } from '@/modules/assets/amount-display/types';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';

interface UseHistoricRateReturn {
  /** Whether a usable timestamp was given, so the caller should use `rate` and not a live price. */
  isHistoric: ComputedRef<boolean>;
  /** Whether the historic rate is still being fetched. Always false for a live lookup. */
  loading: ComputedRef<boolean>;
  /**
   * The cached historic rate at the timestamp. Zero for a live lookup or an empty identifier, and
   * possibly zero or negative while it is loading or when it is unavailable.
   */
  rate: ComputedRef<BigNumber>;
}

/**
 * Looks up the historic price of an asset or currency at an optional timestamp.
 *
 * @remarks
 * A missing, zero or negative timestamp means "no timestamp": the lookup is live, `isHistoric` is
 * false and the caller falls back to its own current price.
 *
 * @param identifier - the asset identifier or currency code to price
 * @param timestamp - when to price it; a bare number is seconds
 */
export function useHistoricRate(
  identifier: MaybeRefOrGetter<string>,
  timestamp: MaybeRefOrGetter<Timestamp | undefined>,
): UseHistoricRateReturn {
  const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();

  const seconds = computed<number | undefined>(() => {
    const ts = normalizeTimestamp(toValue(timestamp));
    return ts !== undefined && ts > 0 ? ts : undefined;
  });

  const isHistoric = computed<boolean>(() => get(seconds) !== undefined);

  const loading = computed<boolean>(() => {
    const id = toValue(identifier);
    const ts = get(seconds);
    return !!id && ts !== undefined && getIsPending(createKey(id, ts));
  });

  const rate = computed<BigNumber>(() => {
    const id = toValue(identifier);
    const ts = get(seconds);
    return id && ts !== undefined ? getHistoricPrice(id, ts) : Zero;
  });

  return {
    isHistoric,
    loading,
    rate,
  };
}
