import { Ref } from "@vue/composition-api";
import VueI18n from 'vue-i18n';
import { SupportedAsset } from "../data";
import { ProfitLossModel } from "../defi";
import { BalancerBalanceWithOwner, BalancerEvent, BalancerProfitLoss, Pool } from "../defi/balancer";
import { DexTrade } from "../defi/dex";
import { XswapBalance, XswapEventDetails, XswapPool, XswapPoolProfit } from "../defi/xswap";
import { AssetBalanceWithPrice, BigNumber } from "../index";
import { Theme , DebugSettings, FrontendSettingsPayload, Themes, TimeUnit } from '../settings';
import { AdexBalances, AdexHistory } from "../staking/adex";
import { LocationData, NetValue, OwnedAssets, TimedAssetBalances, TimedBalances } from "../statistics";

export interface PremiumInterface {
  readonly useHostComponents: boolean;
  readonly version: number;
  readonly api: PremiumApi;
  readonly debug?: DebugSettings;
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
  netValue: (startingData: number) => Ref<NetValue>
}

export interface AdexApi {
  fetchAdex(refresh: boolean): Promise<void>
  adexHistory: Ref<AdexHistory>
  adexBalances: Ref<AdexBalances>
}

export interface DateUtilities {
  epoch(): number;
  format(date: string, oldFormat: string, newFormat: string): string;
  now(format: string): string;
  epochToFormat(epoch: number, format: string): string;
  dateToEpoch(date: string, format: string): number;
  epochStartSubtract(amount: number, unit: TimeUnit): number;
  toUserSelectedFormat(timestamp: number): string;
  getDateInputISOFormat(format: string): string;
  convertToTimestamp(date: string, dateFormat?: string): number;
}

export type DexTradesApi = {
  fetchUniswapTrades: (refresh: boolean) => Promise<void>
  fetchBalancerTrades: (refresh: boolean) => Promise<void>
  fetchSushiswapTrades: (refresh: boolean) => Promise<void>
  dexTrades: (addresses: string[]) => Ref<DexTrade[]>
};

export type CompoundApi = {
  compoundRewards: Ref<ProfitLossModel[]>
  compoundDebtLoss: Ref<ProfitLossModel[]>
  compoundLiquidationProfit: Ref<ProfitLossModel[]>
  compoundInterestProfit: Ref<ProfitLossModel[]>
};

export type BalancerApi = {
  balancerProfitLoss: (addresses: string[]) => Ref<BalancerProfitLoss[]>,
  balancerEvents: (addresses: string[]) => Ref<BalancerEvent[]>,
  balancerBalances: Ref<BalancerBalanceWithOwner[]>,
  balancerPools: Ref<Pool[]>,
  balancerAddresses: Ref<string[]>,
  fetchBalancerBalances: (refresh: boolean) => Promise<void>,
  fetchBalancerEvents: (refresh: boolean) => Promise<void>
};

export type SushiApi = {
  balances: (addresses: string[]) => Ref<XswapBalance[]>
  events: (addresses: string[]) => Ref<XswapEventDetails[]>;
  poolProfit: (addresses: string[]) => Ref<XswapPoolProfit[]>
  addresses: Ref<string[]>
  pools: Ref<XswapPool[]>
  fetchBalances: (refresh: boolean) => Promise<void>
  fetchEvents: (refresh: boolean) => Promise<void>
}

export type BalancesApi = {
  byLocation: Ref<Record<string, BigNumber>>
  aggregatedBalances: Ref<AssetBalanceWithPrice[]>
  exchangeRate: (currency: string) => Ref<BigNumber>
};

export type AssetsApi = {
  assetInfo(identifier: string): SupportedAsset | undefined;
  assetSymbol(identifier: string): string;
  getIdentifierForSymbol(symbol: string): string | undefined;
};

export type UtilsApi = {
  truncate(text: string, length: number): string
};

export interface DataUtilities {
  readonly assets: AssetsApi
  readonly utils: UtilsApi
  readonly statistics: StatisticsApi;
  readonly adex: AdexApi;
  readonly dexTrades: DexTradesApi,
  readonly compound: CompoundApi,
  readonly balancer: BalancerApi,
  readonly balances: BalancesApi
  readonly sushi: SushiApi
}

export type UserSettingsApi = {
  currencySymbol: Ref<string>
  floatingPrecision: Ref<number>
  shouldShowAmount: Ref<boolean>
  shouldShowPercentage: Ref<boolean>
  scrambleData: Ref<boolean>
  selectedTheme: Ref<Theme>
  dateInputFormat: Ref<string>
  privacyMode: Ref<number>
  graphZeroBased: Ref<boolean>
  showGraphRangeSelector: Ref<boolean>
};

export interface SettingsApi {
  update(settings: FrontendSettingsPayload): Promise<void>;
  defaultThemes(): Themes;
  themes(): Themes;
  user: UserSettingsApi;
  i18n: {
    t: typeof VueI18n.prototype.t,
    tc: typeof VueI18n.prototype.tc,
  };
}

export type PremiumApi = {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
  readonly settings: SettingsApi;
};
