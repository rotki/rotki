export interface GeneralSettings {
  readonly floatingPrecision: number;
  readonly anonymizedLogs: boolean;
  readonly historicDataStart: string;
  readonly rpcPort: number;
  readonly balanceSaveFrequency: number;
  readonly dateDisplayFormat: string;
  readonly selectedCurrency: string;
}

interface Credentials {
  readonly username: string;
  readonly password: string;
}
