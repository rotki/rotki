import { currencies } from '@/data/currencies';
import { Defaults } from '@/data/defaults';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export const defaultGeneralSettings = (): GeneralSettings => ({
  floatingPrecision: Defaults.FLOATING_PRECISION,
  ethRpcEndpoint: Defaults.RPC_ENDPOINT,
  ksmRpcEndpoint: Defaults.KSM_RPC_ENDPOINT,
  dotRpcEndpoint: Defaults.DOT_RPC_ENDPOINT,
  balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
  dateDisplayFormat: Defaults.DEFAULT_DATE_DISPLAY_FORMAT,
  anonymousUsageAnalytics: Defaults.ANONYMOUS_USAGE_ANALYTICS,
  selectedCurrency: currencies[0],
  activeModules: [],
  btcDerivationGapLimit: Defaults.BTC_DERIVATION_GAP_LIMIT,
  displayDateInLocaltime: Defaults.DISPLAY_DATE_IN_LOCALTIME,
  currentPriceOracles: [],
  historicalPriceOracles: [],
  ssf0GraphMultiplier: 0
});

export const defaultAccountingSettings = (): AccountingSettings => ({
  haveCSVSummary: false,
  exportCSVFormulas: true,
  includeCrypto2Crypto: true,
  includeGasCosts: true,
  taxFreeAfterPeriod: null,
  accountForAssetsMovements: true,
  calculatePastCostBasis: true,
  taxableLedgerActions: []
});
