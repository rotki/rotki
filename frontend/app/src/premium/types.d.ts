import { TimeUnit } from '@/components/dashboard/types';
import { DebugSettings } from '@/electron-main/ipc';
import { SupportedAsset } from '@/services/assets/types';
import { FrontendSettingsPayload, Themes } from '@/store/settings/types';

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

interface SettingsApi {
  update(settings: FrontendSettingsPayload): Promise<void>;
  defaultThemes(): Themes;
  themes(): Themes;
}

export type ExposedUtilities = {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
  readonly settings: SettingsApi;
};
