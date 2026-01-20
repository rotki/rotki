import type { ComputedRef, Ref } from 'vue';
import type { Currency } from '@/types/currencies';
import type { RoundingMode } from '@/types/settings/frontend-settings';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';

export interface AmountDisplaySettings {
  // General settings
  floatingPrecision: Ref<number>;
  currency: Ref<Currency>;
  currencySymbol: Ref<string>;

  // Frontend settings - formatting
  thousandSeparator: Ref<string>;
  decimalSeparator: Ref<string>;
  currencyLocation: Ref<'before' | 'after'>;
  abbreviateNumber: Ref<boolean>;
  minimumDigitToBeAbbreviated: Ref<number>;
  subscriptDecimals: Ref<boolean>;

  // Frontend settings - rounding
  amountRoundingMode: Ref<RoundingMode>;
  valueRoundingMode: Ref<RoundingMode>;

  // Frontend settings - privacy
  scrambleData: Ref<boolean>;
  scrambleMultiplier: Ref<number | undefined>;
  shouldShowAmount: ComputedRef<boolean>;
}

/**
 * Consolidates all settings needed for AmountDisplay into a single composable.
 * This reduces duplicate store access calls and provides a clean API for settings.
 *
 * Note: Pinia stores are already singletons per pinia instance, so calling this
 * multiple times is efficient - no additional caching is needed.
 */
export function useAmountDisplaySettings(): AmountDisplaySettings {
  const generalSettingsStore = useGeneralSettingsStore();
  const frontendSettingsStore = useFrontendSettingsStore();

  const {
    currency,
    currencySymbol,
    floatingPrecision,
  } = storeToRefs(generalSettingsStore);

  const {
    abbreviateNumber,
    amountRoundingMode,
    currencyLocation,
    decimalSeparator,
    minimumDigitToBeAbbreviated,
    scrambleData,
    scrambleMultiplier,
    shouldShowAmount,
    subscriptDecimals,
    thousandSeparator,
    valueRoundingMode,
  } = storeToRefs(frontendSettingsStore);

  return {
    abbreviateNumber,
    amountRoundingMode,
    currency,
    currencyLocation,
    currencySymbol,
    decimalSeparator,
    floatingPrecision,
    minimumDigitToBeAbbreviated,
    scrambleData,
    scrambleMultiplier,
    shouldShowAmount,
    subscriptDecimals,
    thousandSeparator,
    valueRoundingMode,
  };
}
