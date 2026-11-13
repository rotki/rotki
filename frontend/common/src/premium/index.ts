import type { ComputedRef, MaybeRef, MaybeRefOrGetter, Ref } from 'vue';
import type { AssetBalanceWithPrice } from '../balances';
import type { AssetInfoWithId } from '../data';
import type { BigNumber } from '../numbers';
import type { FrontendSettingsPayload, TimeUnit } from '../settings/frontend';
import type { Themes } from '../settings/themes';
import type {
  CommonQueryStatusData,
  FailedHistoricalAssetPriceResponse,
  HistoricalAssetPricePayload,
  HistoricalAssetPriceResponse,
  LocationData,
  NetValue,
  OwnedAssets,
  ResolvedPrice,
  TimedAssetBalances,
  TimedAssetHistoricalBalances,
  TimedBalances,
} from '../statistics';

export type ExclusionSource = 'exchange' | 'manual' | 'blockchain';

/** A net value series in the main currency. */
export interface EstimatedNetValue extends NetValue {
  /** Per point, whether it was converted at a stand-in rate; absent means none was. */
  readonly estimated?: readonly boolean[];
  /** Per point, when the rate it was converted at was quoted, unix seconds; undefined for today's rate. */
  readonly rateTimes?: readonly (number | undefined)[];
}

export interface StatisticsApi {
  assetValueDistribution: () => Promise<TimedAssetBalances>;
  locationValueDistribution: () => Promise<LocationData>;
  ownedAssets: () => Promise<OwnedAssets>;
  timedBalances: (asset: string, start: number, end: number, collectionId?: number) => Promise<TimedBalances>;
  timedHistoricalBalances: (asset: string, start: number, end: number, collectionId?: number) => Promise<TimedAssetHistoricalBalances>;
  netValue: (startingData: number) => Ref<EstimatedNetValue>;
  isQueryingDailyPrices: ComputedRef<boolean>;
  failedDailyPrices: Ref<Record<string, FailedHistoricalAssetPriceResponse>>;
  queryHistoricalAssetPrices: (payload: HistoricalAssetPricePayload) => Promise<HistoricalAssetPriceResponse>;
  historicalDailyPriceStatus: Ref<CommonQueryStatusData | undefined>;
  cancelHistoricPriceTask: () => Promise<void>;
  cancelDailyHistoricPriceTask: () => Promise<void>;
  /**
   * The USD to main currency rate at each of `times`, for converting values stored in USD such as
   * snapshots.
   *
   * @remarks
   * Call once per graph during setup, with every time it needs: each call reads the cache and
   * fetches what is missing as one series. A rate missing from the cache resolves as a flagged
   * stand-in and is fetched in the background while the calling scope lives.
   *
   * @param times - unix seconds
   * @returns one rate per entry of `times`, in the same order
   */
  usdRatesAt: (times: MaybeRefOrGetter<readonly number[]>) => ComputedRef<readonly ResolvedPrice[]>;
}

export interface DateUtilities {
  epoch: () => number;
  epochStartSubtract: (amount: number, unit: TimeUnit) => number;
  convertToTimestamp: (date: string, dateFormat?: string) => number;
}

export interface BalancesApi {
  byLocation: Ref<Record<string, BigNumber>>;
  balances: (groupMultiChain?: boolean, exclude?: ExclusionSource[]) => ComputedRef<AssetBalanceWithPrice[]>;
  exchangeRate: (currency: string) => Ref<BigNumber>;
  queryOnlyCacheHistoricalRates: (asset: string, timestamp: number[]) => Promise<Record<number, BigNumber>>;
  assetPrice: (asset: string) => ComputedRef<BigNumber>;
}

export interface AssetsApi {
  assetInfo: (identifier: MaybeRef<string>) => ComputedRef<AssetInfoWithId | null>;
  assetSymbol: (identifier: MaybeRef<string>) => ComputedRef<string>;
}

export interface DataUtilities {
  readonly assets: AssetsApi;
  readonly statistics: StatisticsApi;
  readonly balances: BalancesApi;
}

export interface UserSettingsApi {
  currencySymbol: Ref<string>;
  floatingPrecision: Ref<number>;
  decimalSeparator: Ref<string>;
  thousandSeparator: Ref<string>;
  subscriptDecimals: Ref<boolean>;
  shouldShowAmount: Ref<boolean>;
  scrambleData: Ref<boolean>;
  scrambleMultiplier: Ref<number>;
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
  };
}

interface ColorStop {
  color: string;
  offset: number;
}

interface GradientColor {
  colorStops: ColorStop[];
  type: 'linear';
  x: number;
  x2: number;
  y: number;
  y2: number;
}

export interface GradientArea {
  color: GradientColor;
}

export interface NewGraphApi {
  baseColor: ComputedRef<string>;
  gradient: ComputedRef<GradientArea>;
  secondaryColor: ComputedRef<string>;
}

type GetGraphApi = () => NewGraphApi;

export interface LoggerApi {
  error: (...args: any[]) => void;
}

export interface PremiumApi {
  readonly date: DateUtilities;
  readonly data: DataUtilities;
  readonly settings: SettingsApi;
  readonly graphs: GetGraphApi;
  readonly logger: LoggerApi;
}
