import { currencies } from '@/data/currencies';
import { DBSettings } from '@/model/action-result';
import { Currency } from '@/model/currency';
import { AccountingSettings, GeneralSettings } from '@/typing/types';

export const findCurrency = (currencySymbol: string) => {
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
  selectedCurrency: findCurrency(settings.main_currency),
  dateDisplayFormat: settings.date_display_format,
  balanceSaveFrequency: settings.balance_save_frequency,
  ethRpcEndpoint: settings.eth_rpc_endpoint,
  ksmRpcEndpoint: settings.ksm_rpc_endpoint,
  anonymousUsageAnalytics: settings.submit_usage_analytics,
  activeModules: settings.active_modules,
  btcDerivationGapLimit: settings.btc_derivation_gap_limit,
  displayDateInLocaltime: settings.display_date_in_localtime,
  currentPriceOracles: settings.current_price_oracles,
  historicalPriceOracles: settings.historical_price_oracles
});

export const convertToAccountingSettings = (
  settings: DBSettings
): AccountingSettings => ({
  taxFreeAfterPeriod: settings.taxfree_after_period,
  includeGasCosts: settings.include_gas_costs,
  includeCrypto2Crypto: settings.include_crypto2crypto,
  accountForAssetsMovements: settings.account_for_assets_movements,
  calculatePastCostBasis: settings.calculate_past_cost_basis,
  taxableLedgerActions: settings.taxable_ledger_actions
});
