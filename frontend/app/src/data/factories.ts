import { currencies } from '@/data/currencies';
import { Defaults } from '@/data/defaults';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export const defaultSettings = (): GeneralSettings => ({
  floatingPrecision: Defaults.FLOATING_PRECISION,
  anonymizedLogs: Defaults.ANONYMIZED_LOGS,
  ethRpcEndpoint: Defaults.RPC_ENDPOINT,
  balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
  dateDisplayFormat: Defaults.DEFAULT_DISPLAY_FORMAT,
  historicDataStart: Defaults.HISTORICAL_DATA_START,
  anonymousUsageAnalytics: Defaults.ANONYMOUS_USAGE_ANALYTICS,
  selectedCurrency: currencies[0],
  krakenAccountType: Defaults.KRAKEN_DEFAULT_ACCOUNT_TYPE
});

export const defaultAccountingSettings = (): AccountingSettings => ({
  lastBalanceSave: 0,
  includeCrypto2Crypto: true,
  includeGasCosts: true,
  taxFreeAfterPeriod: null
});
