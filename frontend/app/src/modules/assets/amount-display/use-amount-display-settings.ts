import type { Ref } from 'vue';
import type { Currency } from '@/modules/assets/amount-display/currencies';
import type { RoundingMode } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';

export interface AmountDisplaySettings {
  // General settings
  floatingPrecision: Readonly<Ref<number>>;
  currency: Readonly<Ref<Currency>>;
  currencySymbol: Readonly<Ref<string>>;

  // Frontend settings - formatting
  thousandSeparator: Readonly<Ref<string>>;
  decimalSeparator: Readonly<Ref<string>>;
  currencyLocation: Readonly<Ref<'before' | 'after'>>;
  abbreviateNumber: Readonly<Ref<boolean>>;
  minimumDigitToBeAbbreviated: Readonly<Ref<number>>;
  subscriptDecimals: Readonly<Ref<boolean>>;

  // Frontend settings - rounding
  amountRoundingMode: Readonly<Ref<RoundingMode>>;
  valueRoundingMode: Readonly<Ref<RoundingMode>>;

  // Frontend settings - privacy
  scrambleData: Readonly<Ref<boolean>>;
  scrambleMultiplier: Readonly<Ref<number | undefined>>;
  shouldShowAmount: Readonly<Ref<boolean>>;
}

/**
 * Domain facade bundling the settings needed for amount display. Each entry reads through
 * `useSetting`, so this composable knows nothing about which store owns each key and no store is
 * imported here. This is the "several settings consumed together" layer over the per-key primitive.
 */
export function useAmountDisplaySettings(): AmountDisplaySettings {
  return {
    abbreviateNumber: useSetting('abbreviateNumber'),
    amountRoundingMode: useSetting('amountRoundingMode'),
    currency: useSetting('currency'),
    currencyLocation: useSetting('currencyLocation'),
    currencySymbol: useSetting('currencySymbol'),
    decimalSeparator: useSetting('decimalSeparator'),
    floatingPrecision: useSetting('floatingPrecision'),
    minimumDigitToBeAbbreviated: useSetting('minimumDigitToBeAbbreviated'),
    scrambleData: useSetting('scrambleData'),
    scrambleMultiplier: useSetting('scrambleMultiplier'),
    shouldShowAmount: useSetting('shouldShowAmount'),
    subscriptDecimals: useSetting('subscriptDecimals'),
    thousandSeparator: useSetting('thousandSeparator'),
    valueRoundingMode: useSetting('valueRoundingMode'),
  };
}
