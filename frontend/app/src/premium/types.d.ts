import { TimeUnit } from '@/components/dashboard/types';
import { DebugSettings } from '@/electron-main/ipc';
import { SupportedAsset } from '@/services/types-model';

export interface RotkiPremiumInterface {
  readonly useHostComponents: boolean;
  readonly version: number;
  readonly utils: ExposedUtilities;
  readonly debug?: DebugSettings;
}

interface DateUtilities {
  epoch(): number;
  format(date: string, oldFormat: string, newFormat: string): string;
  now(format: string): string;
  epochToFormat(epoch: number, format: string): string;
  dateToEpoch(date: string, format: string): number;
  epochStartSubtract(amount: number, unit: TimeUnit): number;
  toUserSelectedFormat(timestamp: number): string;
}

interface DataUtilities {
  assetInfo(identifier: string): SupportedAsset | undefined;
  getIdentifierForSymbol(symbol: string): string | undefined;
}

export type ExposedUtilities = {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
};
