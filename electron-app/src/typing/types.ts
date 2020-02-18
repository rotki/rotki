import { ApiAssetBalance, AssetBalances } from '@/model/blockchain-balances';
import { Currency } from '@/model/currency';

export interface GeneralSettings {
  readonly floatingPrecision: number;
  readonly anonymizedLogs: boolean;
  readonly anonymousUsageAnalytics: boolean;
  readonly historicDataStart: string;
  readonly ethRpcEndpoint: string;
  readonly balanceSaveFrequency: number;
  readonly dateDisplayFormat: string;
  readonly selectedCurrency: Currency;
}

export interface AccountingSettings {
  readonly lastBalanceSave: number;
  readonly includeCrypto2Crypto: boolean;
  readonly includeGasCosts: boolean;
  readonly taxFreeAfterPeriod: number | null;
}

export interface AccountingSettingsUpdate {
  readonly lastBalanceSave?: number;
  readonly includeCrypto2Crypto?: boolean;
  readonly includeGasCosts?: boolean;
  readonly taxFreeAfterPeriod?: number | null;
}

export interface Credentials {
  readonly username: string;
  readonly password: string;
  readonly syncApproval?: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
}

export type UsdToFiatExchangeRates = { [key: string]: number };

export interface ApiAssetBalances {
  [asset: string]: ApiAssetBalance;
}

export interface ExchangeInfo {
  readonly name: string;
  readonly balances: AssetBalances;
}

export type ExchangeData = { [exchange: string]: AssetBalances };

export enum Severity {
  WARNING = 'warning',
  ERROR = 'error',
  INFO = 'info'
}

export interface NotificationData {
  readonly id: number;
  readonly title: string;
  readonly message: string;
  readonly severity: Severity;
}

export interface TaxReportEvent {
  readonly start: number;
  readonly end: number;
}

export interface FiatExchangeRates {
  [currency: string]: string;
}

export interface AccountSession {
  [account: string]: 'loggedin' | 'loggedout';
}

export interface TaskResult<T> {
  outcome: T | null;
  status: 'completed' | 'not-found' | 'pending';
}

export const SupportedBlockchains = ['ETH', 'BTC'];

export type Blockchain = 'ETH' | 'BTC';

export class SyncConflictError extends Error {}

export type SyncApproval = 'yes' | 'no' | 'unknown';

export interface UnlockPayload {
  readonly username: string;
  readonly password: string;
  readonly create: boolean;
  readonly syncApproval: SyncApproval;
  readonly apiKey?: string;
  readonly apiSecret?: string;
}

export type SettingsUpdate = {
  +readonly [P in keyof SettingsPayload]+?: SettingsPayload[P];
};

export interface SettingsPayload {
  balance_save_frequency: number;
  main_currency: string;
  anonymized_logs: boolean;
  submit_usage_analytics: boolean;
  historical_data_start: string;
  eth_rpc_endpoint: string;
  ui_floating_precision: number;
  date_display_format: string;
  include_gas_costs: boolean;
  include_crypto2crypto: boolean;
  taxfree_after_period: number;
}

export type ExternalServiceName = 'etherscan' | 'cryptocompare';

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
