import { DBSettings } from '@/model/action-result';
import { AccountingSettings, GeneralSettings } from '@/typing/types';
import { currencies } from '@/data/currencies';
import { Currency } from '@/model/currency';

const findCurrency = (currencySymbol: string) => {
  const currency: Currency | undefined = currencies.find(
    currency => currency.ticker_symbol === currencySymbol
  );
  if (!currency) {
    throw new Error(`Could not find ${currencySymbol}`);
  }
  return currency;
};

export const convertToGeneralSettings = (
  settings: DBSettings
): GeneralSettings => ({
  floatingPrecision: settings.ui_floating_precision,
  historicDataStart: settings.historical_data_start,
  selectedCurrency: findCurrency(settings.main_currency),
  dateDisplayFormat: settings.date_display_format,
  balanceSaveFrequency: settings.balance_save_frequency,
  ethRpcEndpoint: settings.eth_rpc_endpoint,
  anonymizedLogs: settings.anonymized_logs,
  anonymousUsageAnalytics: settings.submit_usage_analytics
});

export const convertToAccountingSettings = (
  settings: DBSettings
): AccountingSettings => ({
  taxFreeAfterPeriod: settings.taxfree_after_period,
  includeGasCosts: settings.include_gas_costs,
  includeCrypto2Crypto: settings.include_crypto2crypto,
  lastBalanceSave: settings.last_balance_save
});
