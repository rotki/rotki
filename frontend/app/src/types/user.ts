import { currencies } from '@/data/currencies';
import { Currency } from '@/model/currency';
import { Module } from '@/services/session/consts';
import { Exchange } from '@/types/exchanges';
import { LedgerActionType } from '@/types/ledger-actions';

const PRICE_ORACLES = ['cryptocompare', 'coingecko'] as const;
export type PriceOracles = typeof PRICE_ORACLES[number];

export interface UserAccount {
  readonly premium: boolean;
  readonly settings: UserSettings;
  readonly exchanges: Exchange[];
}

export interface UserSettings {
  readonly taxable_ledger_actions: LedgerActionType[];
  readonly have_premium: boolean;
  readonly version: number;
  readonly last_write_ts: number;
  readonly premium_should_sync?: boolean;
  readonly submit_usage_analytics: boolean;
  readonly include_crypto2crypto: boolean;
  readonly include_gas_costs: boolean;
  readonly last_data_upload_ts: number;
  readonly ui_floating_precision: number;
  readonly taxfree_after_period: number;
  readonly balance_save_frequency: number;
  readonly eth_rpc_endpoint: string;
  readonly ksm_rpc_endpoint: string;
  readonly dot_rpc_endpoint: string;
  readonly main_currency: string;
  readonly last_balance_save: number;
  readonly date_display_format: string;
  readonly kraken_account_type: string;
  readonly active_modules: Module[];
  readonly frontend_settings: string;
  readonly account_for_assets_movements: boolean;
  readonly btc_derivation_gap_limit: number;
  readonly calculate_past_cost_basis: boolean;
  readonly display_date_in_localtime: boolean;
  readonly current_price_oracles: PriceOracles[];
  readonly historical_price_oracles: PriceOracles[];
  readonly pnl_csv_with_formulas: boolean;
  readonly pnl_csv_have_summary: boolean;
  readonly ssf_0graph_multiplier: number;
}

export interface GeneralSettings {
  readonly floatingPrecision: number;
  readonly anonymousUsageAnalytics: boolean;
  readonly ethRpcEndpoint: string;
  readonly ksmRpcEndpoint: string;
  readonly dotRpcEndpoint: string;
  readonly balanceSaveFrequency: number;
  readonly dateDisplayFormat: string;
  readonly selectedCurrency: Currency;
  readonly activeModules: Module[];
  readonly btcDerivationGapLimit: number;
  readonly displayDateInLocaltime: boolean;
  readonly currentPriceOracles: PriceOracles[];
  readonly historicalPriceOracles: PriceOracles[];
  readonly ssf0GraphMultiplier: number;
}

export interface AccountingSettings {
  readonly calculatePastCostBasis: boolean;
  readonly haveCSVSummary: boolean;
  readonly exportCSVFormulas: boolean;
  readonly includeCrypto2Crypto: boolean;
  readonly includeGasCosts: boolean;
  readonly taxFreeAfterPeriod: number | null;
  readonly accountForAssetsMovements: boolean;
  readonly taxableLedgerActions: LedgerActionType[];
}

export type AccountingSettingsUpdate = Partial<AccountingSettings>;
export type SettingsUpdate = Partial<SettingsPayload>;

interface SettingsPayload {
  balance_save_frequency: number;
  main_currency: string;
  submit_usage_analytics: boolean;
  eth_rpc_endpoint: string;
  ksm_rpc_endpoint: string;
  dot_rpc_endpoint: string;
  ui_floating_precision: number;
  date_display_format: string;
  include_gas_costs: boolean;
  include_crypto2crypto: boolean;
  taxfree_after_period: number;
  kraken_account_type: string;
  premium_should_sync: boolean;
  active_modules: Module[];
  frontend_settings: string;
  account_for_assets_movements: boolean;
  btc_derivation_gap_limit: number;
  calculate_past_cost_basis: boolean;
  display_date_in_localtime: boolean;
  current_price_oracles: string[];
  historical_price_oracles: string[];
  taxable_ledger_actions: LedgerActionType[];
  pnl_csv_with_formulas: boolean;
  pnl_csv_have_summary: boolean;
  ssf_0graph_multiplier: number;
}

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
  settings: UserSettings
): GeneralSettings => ({
  floatingPrecision: settings.ui_floating_precision,
  selectedCurrency: findCurrency(settings.main_currency),
  dateDisplayFormat: settings.date_display_format,
  balanceSaveFrequency: settings.balance_save_frequency,
  ethRpcEndpoint: settings.eth_rpc_endpoint,
  ksmRpcEndpoint: settings.ksm_rpc_endpoint,
  dotRpcEndpoint: settings.dot_rpc_endpoint,
  anonymousUsageAnalytics: settings.submit_usage_analytics,
  activeModules: settings.active_modules,
  btcDerivationGapLimit: settings.btc_derivation_gap_limit,
  displayDateInLocaltime: settings.display_date_in_localtime,
  currentPriceOracles: settings.current_price_oracles,
  historicalPriceOracles: settings.historical_price_oracles,
  ssf0GraphMultiplier: settings.ssf_0graph_multiplier
});
export const convertToAccountingSettings = (
  settings: UserSettings
): AccountingSettings => ({
  taxFreeAfterPeriod: settings.taxfree_after_period,
  includeGasCosts: settings.include_gas_costs,
  exportCSVFormulas: settings.pnl_csv_with_formulas,
  haveCSVSummary: settings.pnl_csv_have_summary,
  includeCrypto2Crypto: settings.include_crypto2crypto,
  accountForAssetsMovements: settings.account_for_assets_movements,
  calculatePastCostBasis: settings.calculate_past_cost_basis,
  taxableLedgerActions: settings.taxable_ledger_actions
});
