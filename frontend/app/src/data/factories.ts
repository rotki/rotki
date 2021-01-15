import { currencies } from '@/data/currencies';
import { Defaults } from '@/data/defaults';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export const defaultGeneralSettings = (): GeneralSettings => ({
  floatingPrecision: Defaults.FLOATING_PRECISION,
  anonymizedLogs: Defaults.ANONYMIZED_LOGS,
  ethRpcEndpoint: Defaults.RPC_ENDPOINT,
  ksmRpcEndpoint: Defaults.KSM_RPC_ENDPOINT,
  balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
  dateDisplayFormat: Defaults.DEFAULT_DATE_DISPLAY_FORMAT,
  thousandSeparator: Defaults.DEFAULT_THOUSAND_SEPARATOR,
  decimalSeparator: Defaults.DEFAULT_DECIMAL_SEPARATOR,
  currencyLocation: Defaults.DEFAULT_CURRENCY_LOCATION,
  anonymousUsageAnalytics: Defaults.ANONYMOUS_USAGE_ANALYTICS,
  selectedCurrency: currencies[0],
  krakenAccountType: Defaults.KRAKEN_DEFAULT_ACCOUNT_TYPE,
  activeModules: [],
  btcDerivationGapLimit: Defaults.BTC_DERIVATION_GAP_LIMIT
});

export const defaultAccountingSettings = (): AccountingSettings => ({
  includeCrypto2Crypto: true,
  includeGasCosts: true,
  taxFreeAfterPeriod: null,
  accountForAssetsMovements: true,
  calculatePastCostBasis: true
});
