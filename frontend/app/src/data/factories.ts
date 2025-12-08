import type { Currency } from '@/types/currencies';
import { Defaults } from '@/data/defaults';
import { type AccountingSettings, CostBasisMethod, type GeneralSettings } from '@/types/user';

export function defaultGeneralSettings(mainCurrency: Currency): GeneralSettings {
  return {
    activeModules: [],
    addressNamePriority: [],
    askUserUponSizeDiscrepancy: true,
    autoCreateCalendarReminders: true,
    autoDeleteCalendarEntries: true,
    autoDetectTokens: true,
    balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
    beaconRpcEndpoint: Defaults.BEACON_RPC_ENDPOINT,
    btcDerivationGapLimit: Defaults.BTC_DERIVATION_GAP_LIMIT,
    btcMempoolApi: Defaults.BTC_MEMPOOL_API,
    connectTimeout: Defaults.DEFAULT_CONNECT_TIMEOUT,
    csvExportDelimiter: Defaults.DEFAULT_CSV_EXPORT_DELIMITER,
    currentPriceOracles: [],
    dateDisplayFormat: Defaults.DEFAULT_DATE_DISPLAY_FORMAT,
    defaultEvmIndexerOrder: [],
    displayDateInLocaltime: Defaults.DISPLAY_DATE_IN_LOCALTIME,
    dotRpcEndpoint: Defaults.DOT_RPC_ENDPOINT,
    evmchainsToSkipDetection: [],
    evmIndexersOrder: {},
    historicalPriceOracles: [],
    inferZeroTimedBalances: false,
    ksmRpcEndpoint: Defaults.KSM_RPC_ENDPOINT,
    mainCurrency,
    nonSyncingExchanges: [],
    oraclePenaltyDuration: Defaults.DEFAULT_ORACLE_PENALTY_DURATION,
    oraclePenaltyThresholdCount: Defaults.DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT,
    queryRetryLimit: Defaults.DEFAULT_QUERY_RETRY_LIMIT,
    readTimeout: Defaults.DEFAULT_READ_TIMEOUT,
    ssfGraphMultiplier: 0,
    submitUsageAnalytics: Defaults.ANONYMOUS_USAGE_ANALYTICS,
    treatEth2AsEth: false,
    uiFloatingPrecision: Defaults.FLOATING_PRECISION,
  };
}

export function defaultAccountingSettings(): AccountingSettings {
  return {
    calculatePastCostBasis: true,
    costBasisMethod: CostBasisMethod.FIFO,
    ethStakingTaxableAfterWithdrawalEnabled: false,
    includeCrypto2crypto: true,
    includeFeesInCostBasis: false,
    includeGasCosts: true,
    pnlCsvHaveSummary: false,
    pnlCsvWithFormulas: true,
    taxfreeAfterPeriod: null,
  };
}
