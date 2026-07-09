import type { Ref } from 'vue';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';

/**
 * Read value types are derived from the settings registry via `SettingValue`, so this interface
 * cannot drift from the registry's precise per-key types (e.g. `currencySymbol` stays the currency
 * union rather than widening to `string`).
 */
export interface AmountDisplaySettings {
  // General settings
  floatingPrecision: Readonly<Ref<SettingValue<'floatingPrecision'>>>;
  currency: Readonly<Ref<SettingValue<'currency'>>>;
  currencySymbol: Readonly<Ref<SettingValue<'currencySymbol'>>>;

  // Frontend settings - formatting
  thousandSeparator: Readonly<Ref<SettingValue<'thousandSeparator'>>>;
  decimalSeparator: Readonly<Ref<SettingValue<'decimalSeparator'>>>;
  currencyLocation: Readonly<Ref<SettingValue<'currencyLocation'>>>;
  abbreviateNumber: Readonly<Ref<SettingValue<'abbreviateNumber'>>>;
  minimumDigitToBeAbbreviated: Readonly<Ref<SettingValue<'minimumDigitToBeAbbreviated'>>>;
  subscriptDecimals: Readonly<Ref<SettingValue<'subscriptDecimals'>>>;

  // Frontend settings - rounding
  amountRoundingMode: Readonly<Ref<SettingValue<'amountRoundingMode'>>>;
  valueRoundingMode: Readonly<Ref<SettingValue<'valueRoundingMode'>>>;

  // Frontend settings - privacy
  scrambleData: Readonly<Ref<SettingValue<'scrambleData'>>>;
  scrambleMultiplier: Readonly<Ref<SettingValue<'scrambleMultiplier'>>>;
  shouldShowAmount: Readonly<Ref<SettingValue<'shouldShowAmount'>>>;
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
