import { ActionResult, SupportedAsset } from "../data";
import { GitcoinGrantEventsPayload, GitcoinGrantReport, GitcoinGrants, GitcoinReportPayload } from "../gitcoin";
import { DebugSettings, FrontendSettingsPayload, Themes, TimeUnit } from "../settings";
import { LocationData, OwnedAssets, TimedAssetBalances, TimedBalances } from "../statistics";

export interface RotkiPremiumInterface {
  readonly useHostComponents: boolean;
  readonly version: number;
  readonly utils: ExposedUtilities;
  readonly debug?: DebugSettings;
}

export interface GitCoinApi {
  deleteGrant(grantId: number): Promise<boolean>;
  fetchGrantEvents(
    payload: GitcoinGrantEventsPayload
  ): Promise<ActionResult<GitcoinGrants>>;
  generateReport(payload: GitcoinReportPayload): Promise<GitcoinGrantReport>;
}

export interface StatisticsApi {
  assetValueDistribution(): Promise<TimedAssetBalances>
  locationValueDistribution(): Promise<LocationData>
  ownedAssets(): Promise<OwnedAssets>
  timedBalances(
    asset: string,
    start: number,
    end: number
  ): Promise<TimedBalances>;
}

export interface DateUtilities {
  epoch(): number;
  format(date: string, oldFormat: string, newFormat: string): string;
  now(format: string): string;
  epochToFormat(epoch: number, format: string): string;
  dateToEpoch(date: string, format: string): number;
  epochStartSubtract(amount: number, unit: TimeUnit): number;
  toUserSelectedFormat(timestamp: number): string;
}

export interface DataUtilities {
  assetInfo(identifier: string): SupportedAsset | undefined;
  getIdentifierForSymbol(symbol: string): string | undefined;
  readonly gitcoin: GitCoinApi;
  readonly statistics: StatisticsApi;
}

export interface SettingsApi {
  update(settings: FrontendSettingsPayload): Promise<void>;
  defaultThemes(): Themes;
  themes(): Themes;
}

export type ExposedUtilities = {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
  readonly settings: SettingsApi;
};