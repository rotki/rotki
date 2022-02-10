import { ComputedRef } from "vue-demi";
import { ActionResult, SupportedAsset } from "../data";
import { ProfitLossModel } from "../defi";
import { BalancerBalanceWithOwner, BalancerEvent, BalancerProfitLoss, Pool } from "../defi/balancer";
import { DexTrade } from "../defi/dex";
import { GitcoinGrantEventsPayload, GitcoinGrantReport, GitcoinGrants, GitcoinReportPayload } from "../gitcoin";
import { AssetBalanceWithPrice, BigNumber, SemiPartial } from "../index";
import { Message, NotificationPayload } from "../messages";
import { DebugSettings, FrontendSettingsPayload, Themes, TimeUnit } from "../settings";
import { AdexBalances, AdexHistory } from "../staking/adex";
import { LocationData, NetValue, OwnedAssets, TimedAssetBalances, TimedBalances } from "../statistics";

export interface PremiumInterface {
  readonly useHostComponents: boolean;
  readonly version: number;
  readonly api: PremiumApi;
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
  fetchNetValue(): Promise<void>
  netValue: (startingData: number) => ComputedRef<NetValue>
}

export interface AdexApi {
  fetchAdex(refresh: boolean): Promise<void>
  adexHistory: ComputedRef<AdexHistory>
  adexBalances: ComputedRef<AdexBalances>
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

export type DexTradesApi = {
  fetchUniswapTrades: (refresh: boolean) => Promise<void>
  fetchBalancerTrades: (refresh: boolean) => Promise<void>
  fetchSushiswapTrades: (refresh: boolean) => Promise<void>
  dexTrades: (addresses: string[]) => ComputedRef<DexTrade[]>
};

export type CompoundApi = {
  compoundRewards: ComputedRef<ProfitLossModel[]>
  compoundDebtLoss: ComputedRef<ProfitLossModel[]>
  compoundLiquidationProfit: ComputedRef<ProfitLossModel[]>
  compoundInterestProfit: ComputedRef<ProfitLossModel[]>
};

export type BalancerApi = {
  balancerProfitLoss: (addresses: string[]) => ComputedRef<BalancerProfitLoss[]>,
  balancerEvents: (addresses: string[]) => ComputedRef<BalancerEvent[]>,
  balancerBalances: ComputedRef<BalancerBalanceWithOwner[]>,
  balancerPools: ComputedRef<Pool[]>,
  balancerAddresses: ComputedRef<string[]>,
  fetchBalancerBalances: (refresh: boolean) => Promise<void>,
  fetchBalancerEvents: (refresh: boolean) => Promise<void>
};

export type BalancesApi = {
  byLocation: ComputedRef<Record<string, BigNumber>>
  aggregatedBalances: ComputedRef<AssetBalanceWithPrice[]>
  exchangeRate: (currency: string) => ComputedRef<number>
};

export type AssetsApi = {
  assetInfo(identifier: string): SupportedAsset | undefined;
  getIdentifierForSymbol(symbol: string): string | undefined;
};

export type UtilsApi = {
  truncate(text: string, length: number): string
};

export interface DataUtilities {
  readonly assets: AssetsApi
  readonly utils: UtilsApi
  readonly gitcoin: GitCoinApi;
  readonly statistics: StatisticsApi;
  readonly adex: AdexApi;
  readonly dexTrades: DexTradesApi,
  readonly compound: CompoundApi,
  readonly balancer: BalancerApi,
  readonly balances: BalancesApi
}

export type UserSettingsApi = {
  currencySymbol: ComputedRef<string>
  floatingPrecision: ComputedRef<number>
  shouldShowAmount: ComputedRef<boolean>
  shouldShowPercentage: ComputedRef<boolean>
  scrambleData: ComputedRef<boolean>
  darkModeEnabled: ComputedRef<boolean>
  privacyMode: ComputedRef<boolean>
  graphZeroBased: ComputedRef<boolean>
};

export interface SettingsApi {
  update(settings: FrontendSettingsPayload): Promise<void>;
  defaultThemes(): Themes;
  themes(): Themes;
  user: UserSettingsApi
}

export type PremiumApi = {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
  readonly settings: SettingsApi;
  readonly messages: {
    showMessage(message: Message): void
    notify(notification: SemiPartial<NotificationPayload, 'title' | 'message'>): void
  }
};