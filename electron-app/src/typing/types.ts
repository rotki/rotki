import { ApiAssetBalance } from '@/model/blockchain-balances';
import BigNumber from 'bignumber.js';

export interface GeneralSettings {
  readonly floatingPrecision: number;
  readonly anonymizedLogs: boolean;
  readonly historicDataStart: string;
  readonly ethRpcEndpoint: string;
  readonly balanceSaveFrequency: number;
  readonly dateDisplayFormat: string;
  readonly selectedCurrency: string;
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
}

export type UsdToFiatExchangeRates = { [key: string]: number };

export interface ApiAssetBalances {
  [asset: string]: ApiAssetBalance;
}

export interface ExchangeInfo {
  readonly name: string;
  readonly balances: ApiAssetBalances;
  readonly total: BigNumber;
}

export type ExchangeData = { [exchange: string]: ApiAssetBalances };

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
