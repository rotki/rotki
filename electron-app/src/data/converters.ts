import { DBSettings } from '@/model/action-result';
import { GeneralSettings } from '@/typing/types';

export const convertToGeneralSettings = (
  settings: DBSettings
): GeneralSettings => ({
  floatingPrecision: settings.ui_floating_precision,
  historicDataStart: settings.historical_data_start,
  selectedCurrency: settings.main_currency,
  dateDisplayFormat: settings.date_display_format,
  balanceSaveFrequency: settings.balance_save_frequency,
  rpcPort: parseInt(settings.eth_rpc_port, 10),
  anonymizedLogs: settings.anonymized_logs
});
