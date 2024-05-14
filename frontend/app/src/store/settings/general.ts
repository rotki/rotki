import { defaultGeneralSettings } from '@/data/factories';
import {
  type Currency,
  type SupportedCurrency,
  useCurrencies,
} from '@/types/currencies';
import type { AddressNamePriority } from '@/types/settings/address-name-priorities';
import type { Exchange } from '@/types/exchanges';
import type { Module } from '@/types/modules';
import type { PriceOracle } from '@/types/settings/price-oracle';
import type { GeneralSettings } from '@/types/user';

export const useGeneralSettingsStore = defineStore('settings/general', () => {
  const { defaultCurrency } = useCurrencies();
  const settings = reactive(defaultGeneralSettings(get(defaultCurrency)));

  const uiFloatingPrecision: ComputedRef<number> = computed(
    () => settings.uiFloatingPrecision,
  );
  const submitUsageAnalytics: ComputedRef<boolean> = computed(
    () => settings.submitUsageAnalytics,
  );
  const ksmRpcEndpoint: ComputedRef<string> = computed(
    () => settings.ksmRpcEndpoint,
  );
  const dotRpcEndpoint: ComputedRef<string> = computed(
    () => settings.dotRpcEndpoint,
  );
  const beaconRpcEndpoint: ComputedRef<string> = computed(
    () => settings.beaconRpcEndpoint,
  );
  const balanceSaveFrequency: ComputedRef<number> = computed(
    () => settings.balanceSaveFrequency,
  );
  const dateDisplayFormat: ComputedRef<string> = computed(
    () => settings.dateDisplayFormat,
  );
  const mainCurrency: ComputedRef<Currency> = computed(
    () => settings.mainCurrency,
  );
  const activeModules: ComputedRef<Module[]> = computed(
    () => settings.activeModules,
  );
  const btcDerivationGapLimit: ComputedRef<number> = computed(
    () => settings.btcDerivationGapLimit,
  );
  const displayDateInLocaltime: ComputedRef<boolean> = computed(
    () => settings.displayDateInLocaltime,
  );
  const currentPriceOracles: ComputedRef<PriceOracle[]> = computed(
    () => settings.currentPriceOracles,
  );
  const historicalPriceOracles: ComputedRef<PriceOracle[]> = computed(
    () => settings.historicalPriceOracles,
  );
  const ssfGraphMultiplier: ComputedRef<number> = computed(
    () => settings.ssfGraphMultiplier,
  );
  const inferZeroTimedBalances: ComputedRef<boolean> = computed(
    () => settings.inferZeroTimedBalances,
  );
  const nonSyncingExchanges: ComputedRef<Exchange[]> = computed(
    () => settings.nonSyncingExchanges,
  );
  const evmchainsToSkipDetection: ComputedRef<string[]> = computed(
    () => settings.evmchainsToSkipDetection,
  );
  const treatEth2AsEth: ComputedRef<boolean> = computed(
    () => settings.treatEth2AsEth,
  );
  const addressNamePriority: ComputedRef<AddressNamePriority[]> = computed(
    () => settings.addressNamePriority,
  );
  const queryRetryLimit: ComputedRef<number> = computed(
    () => settings.queryRetryLimit,
  );
  const connectTimeout: ComputedRef<number> = computed(
    () => settings.connectTimeout,
  );
  const readTimeout: ComputedRef<number> = computed(() => settings.readTimeout);

  const oraclePenaltyThresholdCount: ComputedRef<number> = computed(() => settings.oraclePenaltyThresholdCount);

  const oraclePenaltyDuration: ComputedRef<number> = computed(() => settings.oraclePenaltyDuration);

  const autoDeleteCalendarEntries: ComputedRef<boolean> = computed(() => settings.autoDeleteCalendarEntries);

  const autoCreateCalendarReminders: ComputedRef<boolean> = computed(() => settings.autoCreateCalendarReminders);

  const askUserUponSizeDiscrepancy: ComputedRef<boolean> = computed(() => settings.askUserUponSizeDiscrepancy);

  const currencySymbol: ComputedRef<SupportedCurrency> = computed(() => {
    const currency = get(mainCurrency);
    return currency.tickerSymbol;
  });

  const floatingPrecision: ComputedRef<number> = uiFloatingPrecision;
  const currency: ComputedRef<Currency> = mainCurrency;

  const update = (generalSettings: GeneralSettings): void => {
    Object.assign(settings, generalSettings);
  };

  return {
    floatingPrecision,
    submitUsageAnalytics,
    ksmRpcEndpoint,
    dotRpcEndpoint,
    beaconRpcEndpoint,
    balanceSaveFrequency,
    dateDisplayFormat,
    currency,
    currencySymbol,
    activeModules,
    btcDerivationGapLimit,
    displayDateInLocaltime,
    currentPriceOracles,
    historicalPriceOracles,
    ssfGraphMultiplier,
    inferZeroTimedBalances,
    nonSyncingExchanges,
    evmchainsToSkipDetection,
    treatEth2AsEth,
    addressNamePriority,
    queryRetryLimit,
    connectTimeout,
    readTimeout,
    oraclePenaltyThresholdCount,
    oraclePenaltyDuration,
    autoDeleteCalendarEntries,
    autoCreateCalendarReminders,
    askUserUponSizeDiscrepancy,
    // return settings on development for state persistence
    ...(checkIfDevelopment() ? { settings } : {}),
    update,
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useGeneralSettingsStore, import.meta.hot),
  );
}
