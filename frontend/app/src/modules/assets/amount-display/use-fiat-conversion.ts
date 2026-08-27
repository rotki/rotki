import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, One, Zero } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { normalizeTimestamp, type Timestamp } from '@/modules/assets/amount-display/types';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display/use-amount-display-settings';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';

export interface UseFiatConversionOptions {
  /** The value to convert */
  value: MaybeRefOrGetter<BigNumber | undefined>;
  /** Source currency code (e.g., 'USD', 'EUR') */
  from: MaybeRefOrGetter<string>;
  /** Timestamp for historic rate lookup */
  timestamp?: MaybeRefOrGetter<Timestamp | undefined>;
}

export interface UseFiatConversionReturn {
  /** The value converted to the user's display currency */
  converted: ComputedRef<BigNumber>;
  /** Whether conversion rate lookup is in progress */
  loading: ComputedRef<boolean>;
}

/**
 * Converts fiat values from one currency to the user's display currency.
 *
 * @remarks
 * A timestamp selects the historic rate, its absence the live one, and a source currency equal to
 * the user's converts nothing. The historic path resolves to zero, not to the unconverted value,
 * while the rate is still being fetched or when it turns out to be unavailable, so read `loading`
 * before showing `converted`.
 */
export function useFiatConversion(options: UseFiatConversionOptions): UseFiatConversionReturn {
  const {
    from,
    timestamp,
    value,
  } = options;

  const { currencySymbol } = useAmountDisplaySettings();
  const { getExchangeRate } = usePriceUtils();
  const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();

  const timestampToUse = computed<number>(() => {
    const ts = normalizeTimestamp(toValue(timestamp));
    if (ts === undefined || ts <= 0) {
      return -1;
    }
    return ts;
  });

  const loading = computed<boolean>(() => {
    const fromVal = toValue(from);
    const ts = get(timestampToUse);

    if (!fromVal) {
      return false;
    }

    if (ts > 0) {
      return getIsPending(createKey(fromVal, ts));
    }

    return false;
  });

  /**
   * Converts value using current exchange rates (for real-time conversion)
   */
  const latestConvertedValue = computed<BigNumber>(() => {
    const currentValue = toValue(value);
    if (!currentValue) {
      return Zero;
    }

    const to = get(currencySymbol);
    const fromVal = toValue(from);

    if (!fromVal || to === fromVal) {
      return currentValue;
    }

    const multiplierRate = to === CURRENCY_USD ? One : getExchangeRate(to);
    const dividerRate = fromVal === CURRENCY_USD ? One : getExchangeRate(fromVal);

    if (!multiplierRate || !dividerRate) {
      return currentValue;
    }

    return currentValue.multipliedBy(multiplierRate).dividedBy(dividerRate);
  });

  const converted = computed<BigNumber>(() => {
    const currentValue = toValue(value);
    if (!currentValue) {
      return Zero;
    }

    const to = get(currencySymbol);
    const fromVal = toValue(from);
    const ts = get(timestampToUse);

    if (!fromVal || to === fromVal) {
      return currentValue;
    }

    if (ts > 0) {
      const historicRate = getHistoricPrice(fromVal, ts);

      if (historicRate.isPositive()) {
        return currentValue.multipliedBy(historicRate);
      }

      return Zero;
    }

    return get(latestConvertedValue);
  });

  return {
    converted,
    loading,
  };
}
