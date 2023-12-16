import { defaultGeneralSettings } from '@/data/factories';
import { type Currency, type SupportedCurrency, useCurrencies } from '@/types/currencies';
import type { AddressNamePriority } from '@/types/settings/address-name-priorities';
import type { Exchange } from '@/types/exchanges';
import type { Module } from '@/types/modules';
import type { PriceOracle } from '@/types/settings/price-oracle';
import type { GeneralSettings } from '@/types/user';

export const useGeneralSettingsStore = defineStore('settings/general', () => {
  const { defaultCurrency } = useCurrencies();
  const settings = reactive(defaultGeneralSettings(get(defaultCurrency)));

  const uiFloatingPrecision = computed<number>(() => settings.uiFloatingPrecision);
  const submitUsageAnalytics = computed<boolean>(() => settings.submitUsageAnalytics);
  const ksmRpcEndpoint = computed<string>(() => settings.ksmRpcEndpoint);
  const dotRpcEndpoint = computed<string>(() => settings.dotRpcEndpoint);
  const beaconRpcEndpoint = computed<string>(() => settings.beaconRpcEndpoint);
  const balanceSaveFrequency = computed<number>(() => settings.balanceSaveFrequency);
  const dateDisplayFormat = computed<string>(() => settings.dateDisplayFormat);
  const mainCurrency = computed<Currency>(() => settings.mainCurrency);
  const activeModules = computed<Module[]>(() => settings.activeModules);
  const btcDerivationGapLimit = computed<number>(() => settings.btcDerivationGapLimit);
  const displayDateInLocaltime = computed<boolean>(() => settings.displayDateInLocaltime);
  const currentPriceOracles = computed<PriceOracle[]>(() => settings.currentPriceOracles);
  const historicalPriceOracles = computed<PriceOracle[]>(() => settings.historicalPriceOracles);
  const ssfGraphMultiplier = computed<number>(() => settings.ssfGraphMultiplier);
  const inferZeroTimedBalances = computed<boolean>(() => settings.inferZeroTimedBalances);
  const nonSyncingExchanges = computed<Exchange[]>(() => settings.nonSyncingExchanges);
  const evmchainsToSkipDetection = computed<string[]>(() => settings.evmchainsToSkipDetection);
  const treatEth2AsEth = computed<boolean>(() => settings.treatEth2AsEth);
  const addressNamePriority = computed<AddressNamePriority[]>(() => settings.addressNamePriority);
  const queryRetryLimit = computed<number>(() => settings.queryRetryLimit);
  const connectTimeout = computed<number>(() => settings.connectTimeout);
  const readTimeout = computed<number>(() => settings.readTimeout);

  const oraclePenaltyThresholdCount = computed<number>(() => settings.oraclePenaltyThresholdCount);

  const oraclePenaltyDuration = computed<number>(() => settings.oraclePenaltyDuration);

  const autoDeleteCalendarEntries = computed<boolean>(() => settings.autoDeleteCalendarEntries);

  const autoCreateCalendarReminders = computed<boolean>(() => settings.autoCreateCalendarReminders);

  const askUserUponSizeDiscrepancy = computed<boolean>(() => settings.askUserUponSizeDiscrepancy);

  const autoDetectTokens = computed<boolean>(() => settings.autoDetectTokens);

  const currencySymbol = computed<SupportedCurrency>(() => {
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
    autoDetectTokens,
    // return settings on development for state persistence
    ...(checkIfDevelopment() ? { settings } : {}),
    update,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useGeneralSettingsStore, import.meta.hot));
