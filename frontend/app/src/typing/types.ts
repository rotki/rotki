import { default as BigNumber } from 'bignumber.js';
import { PriceOracles } from '@/model/action-result';
import { Currency } from '@/model/currency';
import { SupportedDefiProtocols } from '@/services/defi/types';
import { SupportedModules } from '@/services/session/types';
import { AssetBalances } from '@/store/balances/types';
import { LedgerActionType } from '@/store/history/consts';
import { SyncConflictPayload } from '@/store/session/types';

export const CURRENCY_BEFORE = 'before';
export const CURRENCY_AFTER = 'after';

export const CURRENCY_LOCATION = [CURRENCY_AFTER, CURRENCY_BEFORE] as const;
export type CurrencyLocation = typeof CURRENCY_LOCATION[number];

export interface GeneralSettings {
  readonly floatingPrecision: number;
  readonly anonymousUsageAnalytics: boolean;
  readonly ethRpcEndpoint: string;
  readonly ksmRpcEndpoint: string;
  readonly balanceSaveFrequency: number;
  readonly dateDisplayFormat: string;
  readonly selectedCurrency: Currency;
  readonly activeModules: SupportedModules[];
  readonly btcDerivationGapLimit: number;
  readonly displayDateInLocaltime: boolean;
  readonly currentPriceOracles: PriceOracles[];
  readonly historicalPriceOracles: PriceOracles[];
}

export interface AccountingSettings {
  readonly calculatePastCostBasis: boolean;
  readonly includeCrypto2Crypto: boolean;
  readonly includeGasCosts: boolean;
  readonly taxFreeAfterPeriod: number | null;
  readonly accountForAssetsMovements: boolean;
  readonly taxableLedgerActions: LedgerActionType[];
}

export type AccountingSettingsUpdate = {
  +readonly [P in keyof AccountingSettings]+?: AccountingSettings[P];
};

export interface Credentials {
  readonly username: string;
  readonly password: string;
  readonly syncApproval?: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
  readonly submitUsageAnalytics?: boolean;
}

export type ExchangeRates = { [key: string]: BigNumber };

export interface ExchangeInfo {
  readonly location: string;
  readonly balances: AssetBalances;
  readonly total: BigNumber;
}

export type ExchangeData = { [exchange: string]: AssetBalances };

export interface ProfitLossPeriod {
  readonly start: number;
  readonly end: number;
}

export interface AccountSession {
  [account: string]: 'loggedin' | 'loggedout';
}

export interface TaskResult<T> {
  outcome: T | null;
  status: 'completed' | 'not-found' | 'pending';
}

export const ETH = 'ETH';
export const BTC = 'BTC';
export const KSM = 'KSM';

export const SupportedBlockchains = [ETH, BTC, KSM] as const;

export type Blockchain = typeof SupportedBlockchains[number];

export const L2_LOOPRING = 'LRC';
export const L2_PROTOCOLS = [L2_LOOPRING] as const;
export type SupportedL2Protocol = typeof L2_PROTOCOLS[number];

export class SyncConflictError extends Error {
  readonly payload: SyncConflictPayload;

  constructor(message: string, payload: SyncConflictPayload) {
    super(message);
    this.payload = payload;
  }
}

export type SyncApproval = 'yes' | 'no' | 'unknown';

export interface UnlockPayload {
  readonly username: string;
  readonly password: string;
  readonly create?: boolean;
  readonly syncApproval?: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
  readonly submitUsageAnalytics?: boolean;
  readonly restore?: boolean;
}

export type SettingsUpdate = {
  +readonly [P in keyof SettingsPayload]+?: SettingsPayload[P];
};

interface SettingsPayload {
  balance_save_frequency: number;
  main_currency: string;
  submit_usage_analytics: boolean;
  eth_rpc_endpoint: string;
  ksm_rpc_endpoint: string;
  ui_floating_precision: number;
  date_display_format: string;
  include_gas_costs: boolean;
  include_crypto2crypto: boolean;
  taxfree_after_period: number;
  kraken_account_type: string;
  premium_should_sync: boolean;
  active_modules: SupportedModules[];
  frontend_settings: string;
  account_for_assets_movements: boolean;
  btc_derivation_gap_limit: number;
  calculate_past_cost_basis: boolean;
  display_date_in_localtime: boolean;
  current_price_oracles: string[];
  historical_price_oracles: string[];
  taxable_ledger_actions: LedgerActionType[];
}

export type ExternalServiceName = 'etherscan' | 'cryptocompare' | 'loopring';

export interface ExternalServiceKey {
  readonly name: ExternalServiceName;
  readonly api_key: string;
}

export interface Tag {
  readonly name: string;
  readonly description: string;
  readonly background_color: string;
  readonly foreground_color: string;
}

export interface Tags {
  [tag: string]: Tag;
}

export interface AccountData {
  readonly address: string;
  readonly label: string;
  readonly tags: string[];
}

export interface Account {
  readonly chain: Blockchain;
  readonly address: string;
}

export interface DefiAccount extends Account {
  readonly protocols: SupportedDefiProtocols[];
}

export interface GeneralAccount extends AccountData, Account {}
