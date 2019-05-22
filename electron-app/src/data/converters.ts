import { DBSettings } from '@/model/action-result';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export const convertToGeneralSettings = (
  settings: DBSettings
): GeneralSettings => ({
  floatingPrecision: settings.ui_floating_precision,
  historicDataStart: settings.historical_data_start,
  selectedCurrency: settings.main_currency,
  dateDisplayFormat: settings.date_display_format,
  balanceSaveFrequency: settings.balance_save_frequency,
  ethRpcEndpoint: settings.eth_rpc_endpoint,
  anonymizedLogs: settings.anonymized_logs
});

export const convertToAccountingSettings = (
  settings: DBSettings
): AccountingSettings => ({
  taxFreeAfterPeriod: settings.taxfree_after_period,
  includeGasCosts: settings.include_gas_costs,
  includeCrypto2Crypto: settings.include_crypto2crypto,
  lastBalanceSave: settings.last_balance_save
});
