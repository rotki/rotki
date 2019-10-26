import { GeneralSettings } from '@/typing/types';
import { Defaults } from '@/data/defaults';

export const defaultSettings = (): GeneralSettings => ({
  floatingPrecision: Defaults.FLOATING_PRECISION,
  anonymizedLogs: Defaults.ANONYMIZED_LOGS,
  rpcPort: Defaults.RPC_PORT,
  balanceSaveFrequency: Defaults.BALANCE_SAVE_FREQUENCY,
  dateDisplayFormat: Defaults.DEFAULT_DISPLAY_FORMAT,
  historicDataStart: Defaults.HISTORICAL_DATA_START,
  selectedCurrency: 'USD'
});
