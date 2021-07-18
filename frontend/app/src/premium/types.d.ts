import { TimeUnit } from '@/components/dashboard/types';
import { DebugSettings } from '@/electron-main/ipc';
import { SupportedAsset } from '@/services/assets/types';
import {
  GitcoinGrants,
  GitcoinGrantEventsPayload,
  GitcoinGrantReport,
  GitcoinReportPayload
} from '@/services/history/types';
import { ActionResult } from '@/services/types-api';
import { FrontendSettingsPayload, Themes } from '@/store/settings/types';

export interface RotkiPremiumInterface {
  readonly useHostComponents: boolean;
  readonly version: number;
  readonly utils: ExposedUtilities;
  readonly debug?: DebugSettings;
}

interface GitCoinApi {
  deleteGrant(grantId: number): Promise<boolean>;
  fetchGrantEvents(
    payload: GitcoinGrantEventsPayload
  ): Promise<ActionResult<GitcoinGrants>>;
  generateReport(payload: GitcoinReportPayload): Promise<GitcoinGrantReport>;
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
  readonly gitcoin: GitCoinApi;
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
