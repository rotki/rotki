import type {
  HistoricalAssetPricePayload,
  HistoricalAssetPriceResponse,
  HistoricalPriceQueryStatusData,
  LocationData,
  NetValue,
  OwnedAssets,
  TimedAssetBalances,
  TimedAssetHistoricalBalances,
  TimedBalances,
} from '../statistics';
import type { Theme, Themes } from '../settings/themes';
import type { DebugSettings, FrontendSettingsPayload, TimeUnit } from '../settings/frontend';
import type { LpType, ProfitLossModel } from '../defi/common';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import type { AssetInfo } from '../data';
import type { XswapBalance, XswapPool, XswapPoolProfit } from '../defi/xswap';
import type { BigNumber } from '../numbers';
import type { AssetBalanceWithPrice } from '../balances';

export interface PremiumInterface {
  readonly useHostComponents: boolean;
  readonly version: number;
  readonly api: () => PremiumApi;
  readonly debug?: DebugSettings;
}

export interface StatisticsApi {
  assetValueDistribution: () => Promise<TimedAssetBalances>;
  locationValueDistribution: () => Promise<LocationData>;
  ownedAssets: () => Promise<OwnedAssets>;
  timedBalances: (asset: string, start: number, end: number, collectionId?: number) => Promise<TimedBalances>;
  timedHistoricalBalances: (asset: string, start: number, end: number, collectionId?: number) => Promise<TimedAssetHistoricalBalances>;
  fetchNetValue: () => Promise<void>;
  netValue: (startingData: number) => Ref<NetValue>;
  isQueryingDailyPrices: ComputedRef<boolean>;
  queryHistoricalAssetPrices: (payload: HistoricalAssetPricePayload) => Promise<HistoricalAssetPriceResponse>;
  historicalAssetPriceStatus: Ref<HistoricalPriceQueryStatusData | undefined>;
}

export interface DateUtilities {
  epoch: () => number;
  format: (date: string, oldFormat: string, newFormat: string) => string;
  now: (format: string) => string;
  epochToFormat: (epoch: number, format: string) => string;
  dateToEpoch: (date: string, format: string) => number;
  epochStartSubtract: (amount: number, unit: TimeUnit) => number;
  toUserSelectedFormat: (timestamp: number) => string;
  getDateInputISOFormat: (format: string) => string;
  convertToTimestamp: (date: string, dateFormat?: string) => number;
}

export interface CompoundApi {
  compoundRewards: Ref<ProfitLossModel[]>;
  compoundDebtLoss: Ref<ProfitLossModel[]>;
  compoundLiquidationProfit: Ref<ProfitLossModel[]>;
  compoundInterestProfit: Ref<ProfitLossModel[]>;
}

export interface SushiApi {
  balances: (addresses: string[]) => Ref<XswapBalance[]>;
  poolProfit: (addresses: string[]) => Ref<XswapPoolProfit[]>;
  addresses: Ref<string[]>;
  pools: Ref<XswapPool[]>;
  fetchBalances: (refresh: boolean) => Promise<void>;
  fetchEvents: (refresh: boolean) => Promise<void>;
}

export interface BalancesApi {
  byLocation: Ref<Record<string, BigNumber>>;
  aggregatedBalances: Ref<AssetBalanceWithPrice[]>;
  balances: (groupMultiChain?: boolean) => ComputedRef<AssetBalanceWithPrice[]>;
  exchangeRate: (currency: string) => Ref<BigNumber>;
  historicPriceInCurrentCurrency: (asset: string, timestamp: number) => ComputedRef<BigNumber>;
  queryOnlyCacheHistoricalRates: (asset: string, timestamp: number[]) => Promise<Record<number, BigNumber>>;
  assetPrice: (asset: string) => ComputedRef<BigNumber>;
  isHistoricPricePending: (asset: string, timestamp: number) => ComputedRef<boolean>;
}

export interface AssetsApi {
  assetInfo: (identifier: MaybeRef<string>) => ComputedRef<AssetInfo | null>;
  assetSymbol: (identifier: MaybeRef<string>) => ComputedRef<string>;
  tokenAddress: (identifier: MaybeRef<string>) => ComputedRef<string>;
}

export interface UtilsApi {
  truncate: (text: string, length: number) => string;
  getPoolName: (type: LpType, assets: string[]) => string;
}

export interface DataUtilities {
  readonly assets: AssetsApi;
  readonly utils: UtilsApi;
  readonly statistics: StatisticsApi;
  readonly compound: CompoundApi;
  readonly balances: BalancesApi;
  readonly sushi: SushiApi;
}

export interface UserSettingsApi {
  currencySymbol: Ref<string>;
  floatingPrecision: Ref<number>;
  decimalSeparator: Ref<string>;
  thousandSeparator: Ref<string>;
  subscriptDecimals: Ref<boolean>;
  shouldShowAmount: Ref<boolean>;
  shouldShowPercentage: Ref<boolean>;
  scrambleData: Ref<boolean>;
  scrambleMultiplier: Ref<number>;
  selectedTheme: Ref<Theme>;
  dateInputFormat: Ref<string>;
  privacyMode: Ref<number>;
  graphZeroBased: Ref<boolean>;
  showGraphRangeSelector: Ref<boolean>;
  useHistoricalAssetBalances: Ref<boolean>;
}

export interface SettingsApi {
  update: (settings: FrontendSettingsPayload) => Promise<void>;
  defaultThemes: () => Themes;
  themes: () => Themes;
  isDark: ComputedRef<boolean>;
  user: UserSettingsApi;
  i18n: {
    t: (key: string, values?: Record<string, unknown>, choice?: number) => string;
    te: (key: string) => boolean;
  };
}

export type GraphApi = (canvasId: string) => {
  getCanvasCtx: () => CanvasRenderingContext2D;
  baseColor: ComputedRef<string>;
  gradient: ComputedRef<CanvasGradient>;
  secondaryColor: ComputedRef<string>;
  backgroundColor: ComputedRef<string>;
  fontColor: ComputedRef<string>;
  gridColor: ComputedRef<string>;
  thirdColor: ComputedRef<string>;
};

export interface PremiumApi {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
  readonly settings: SettingsApi;
  readonly graphs: GraphApi;
}
