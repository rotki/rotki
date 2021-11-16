import { currencies } from '@/data/currencies';
import { Defaults } from '@/data/defaults';
import { AccountingSettings, GeneralSettings } from '@/types/user';

export const defaultGeneralSettings = (): GeneralSettings => ({
  uiFloatingPrecision: Defaults.FLOATING_PRECISION,
  ethRpcEndpoint: Defaults.RPC_ENDPOINT,
  ksmRpcEndpoint: Defaults.KSM_RPC_ENDPOINT,
  dotRpcEndpoint: Defaults.DOT_RPC_ENDPOINT,
  balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
  dateDisplayFormat: Defaults.DEFAULT_DATE_DISPLAY_FORMAT,
  submitUsageAnalytics: Defaults.ANONYMOUS_USAGE_ANALYTICS,
  mainCurrency: currencies[0],
  activeModules: [],
  btcDerivationGapLimit: Defaults.BTC_DERIVATION_GAP_LIMIT,
  displayDateInLocaltime: Defaults.DISPLAY_DATE_IN_LOCALTIME,
  currentPriceOracles: [],
  historicalPriceOracles: [],
  ssf0graphMultiplier: 0
});

export const defaultAccountingSettings = (): AccountingSettings => ({
  pnlCsvHaveSummary: false,
  pnlCsvWithFormulas: true,
  includeCrypto2crypto: true,
  includeGasCosts: true,
  taxfreeAfterPeriod: null,
  accountForAssetsMovements: true,
  calculatePastCostBasis: true,
  taxableLedgerActions: []
});
