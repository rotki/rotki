import { Defaults } from '@/data/defaults';
import {
  type AccountingSettings,
  CostBasisMethod,
  type GeneralSettings,
} from '@/types/user';
import type { Currency } from '@/types/currencies';

export function defaultGeneralSettings(mainCurrency: Currency): GeneralSettings {
  return {
    uiFloatingPrecision: Defaults.FLOATING_PRECISION,
    ksmRpcEndpoint: Defaults.KSM_RPC_ENDPOINT,
    dotRpcEndpoint: Defaults.DOT_RPC_ENDPOINT,
    beaconRpcEndpoint: Defaults.BEACON_RPC_ENDPOINT,
    balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
    dateDisplayFormat: Defaults.DEFAULT_DATE_DISPLAY_FORMAT,
    submitUsageAnalytics: Defaults.ANONYMOUS_USAGE_ANALYTICS,
    mainCurrency,
    activeModules: [],
    btcDerivationGapLimit: Defaults.BTC_DERIVATION_GAP_LIMIT,
    displayDateInLocaltime: Defaults.DISPLAY_DATE_IN_LOCALTIME,
    currentPriceOracles: [],
    historicalPriceOracles: [],
    ssfGraphMultiplier: 0,
    inferZeroTimedBalances: false,
    nonSyncingExchanges: [],
    evmchainsToSkipDetection: [],
    treatEth2AsEth: false,
    addressNamePriority: [],
    queryRetryLimit: Defaults.DEFAULT_QUERY_RETRY_LIMIT,
    connectTimeout: Defaults.DEFAULT_CONNECT_TIMEOUT,
    readTimeout: Defaults.DEFAULT_READ_TIMEOUT,
    oraclePenaltyThresholdCount: Defaults.DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT,
    oraclePenaltyDuration: Defaults.DEFAULT_ORACLE_PENALTY_DURATION,
    autoDeleteCalendarEntries: true,
    autoCreateCalendarReminders: true,
    askUserUponSizeDiscrepancy: true,
  };
}

export function defaultAccountingSettings(): AccountingSettings {
  return {
    pnlCsvHaveSummary: false,
    pnlCsvWithFormulas: true,
    includeCrypto2crypto: true,
    includeGasCosts: true,
    taxfreeAfterPeriod: null,
    accountForAssetsMovements: true,
    calculatePastCostBasis: true,
    ethStakingTaxableAfterWithdrawalEnabled: false,
    includeFeesInCostBasis: false,
    costBasisMethod: CostBasisMethod.FIFO,
  };
}
