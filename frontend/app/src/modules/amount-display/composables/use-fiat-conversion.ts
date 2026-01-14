import type { ComputedRef, MaybeRef } from 'vue';
import { type BigNumber, One, Zero } from '@rotki/common';
import { useAmountDisplaySettings } from '@/modules/amount-display/composables/use-amount-display-settings';
import { normalizeTimestamp, type Timestamp } from '@/modules/amount-display/types';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { CURRENCY_USD } from '@/types/currencies';

export interface UseFiatConversionOptions {
  /** The value to convert */
  value: MaybeRef<BigNumber | undefined>;
  /** Source currency code (e.g., 'USD', 'EUR') */
  from: MaybeRef<string>;
  /** Timestamp for historic rate lookup */
  timestamp?: MaybeRef<Timestamp | undefined>;
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
 * Handles:
 * - Real-time currency conversion using exchange rates
 * - Historic currency conversion when timestamp is provided
 * - No conversion when source equals user's currency
 */
export function useFiatConversion(options: UseFiatConversionOptions): UseFiatConversionReturn {
  const {
    from,
    timestamp,
    value,
  } = options;

  const { currencySymbol } = useAmountDisplaySettings();
  const { useExchangeRate } = usePriceUtils();
  const { createKey, historicPriceInCurrentCurrency, isPending } = useHistoricCachePriceStore();

  const timestampToUse = computed<number>(() => {
    const ts = normalizeTimestamp(get(timestamp));
    if (ts === undefined || ts <= 0) {
      return -1;
    }
    return ts;
  });

  const loading = computed<boolean>(() => {
    const fromVal = get(from);
    const ts = get(timestampToUse);

    if (!fromVal) {
      return false;
    }

    if (ts > 0) {
      return get(isPending(createKey(fromVal, ts)));
    }

    return false;
  });

  /**
   * Converts value using current exchange rates (for real-time conversion)
   */
  const latestConvertedValue = computed<BigNumber>(() => {
    const currentValue = get(value);
    if (!currentValue) {
      return Zero;
    }

    const to = get(currencySymbol);
    const fromVal = get(from);

    // No conversion needed if currencies match or no source specified
    if (!fromVal || to === fromVal) {
      return currentValue;
    }

    // Get exchange rates
    const multiplierRate = to === CURRENCY_USD ? One : get(useExchangeRate(to));
    const dividerRate = fromVal === CURRENCY_USD ? One : get(useExchangeRate(fromVal));

    if (!multiplierRate || !dividerRate) {
      return currentValue;
    }

    return currentValue.multipliedBy(multiplierRate).dividedBy(dividerRate);
  });

  const converted = computed<BigNumber>(() => {
    const currentValue = get(value);
    if (!currentValue) {
      return Zero;
    }

    const to = get(currencySymbol);
    const fromVal = get(from);
    const ts = get(timestampToUse);

    // No conversion needed if currencies match
    if (!fromVal || to === fromVal) {
      return currentValue;
    }

    // Use historic rate if timestamp is provided
    if (ts > 0) {
      const historicRate = get(historicPriceInCurrentCurrency(fromVal, ts));

      if (historicRate.isPositive()) {
        return currentValue.multipliedBy(historicRate);
      }

      // If historic rate not available, return zero (still loading or unavailable)
      return Zero;
    }

    // Use real-time conversion
    return get(latestConvertedValue);
  });

  return {
    converted,
    loading,
  };
}
