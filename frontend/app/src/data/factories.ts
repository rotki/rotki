import { Defaults } from '@/data/defaults';
import { type Currency } from '@/types/currencies';
import {
  type AccountingSettings,
  CostBasisMethod,
  type GeneralSettings
} from '@/types/user';

export const defaultGeneralSettings = (
  mainCurrency: Currency
): GeneralSettings => ({
  uiFloatingPrecision: Defaults.FLOATING_PRECISION,
  ksmRpcEndpoint: Defaults.KSM_RPC_ENDPOINT,
  dotRpcEndpoint: Defaults.DOT_RPC_ENDPOINT,
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
  readTimeout: Defaults.DEFAULT_READ_TIMEOUT
});

export const defaultAccountingSettings = (): AccountingSettings => ({
  pnlCsvHaveSummary: false,
  pnlCsvWithFormulas: true,
  includeCrypto2crypto: true,
  includeGasCosts: true,
  taxfreeAfterPeriod: null,
  accountForAssetsMovements: true,
  calculatePastCostBasis: true,
  ethStakingTaxableAfterWithdrawalEnabled: false,
  includeFeesInCostBasis: false,
  costBasisMethod: CostBasisMethod.FIFO
});
