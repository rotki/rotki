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

interface Credentials {
  readonly username: string;
  readonly password: string;
}

interface AccountData {
  readonly username: string;
  readonly password: string;
  readonly apiKey: string;
  readonly apiSecret: string;
}

type UsdToFiatExchangeRates = { [key: string]: number };

export type Balances = { [asset: string]: AssetBalance };

interface AssetInformation {
  readonly name: string;
  readonly amount: number;
  readonly usdValue: number;
}
