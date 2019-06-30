import { AssetBalance } from '@/model/asset-balance';

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

export interface AccountData {
  readonly username: string;
  readonly password: string;
  readonly apiKey: string;
  readonly apiSecret: string;
}

export type UsdToFiatExchangeRates = { [key: string]: number };

export type Balances = { [asset: string]: AssetBalance };

export type ExchangeInfo = {
  name: string;
  balances: Balances;
  totals?: number;
};

export type ExchangeData = { [exchange: string]: Balances };

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
