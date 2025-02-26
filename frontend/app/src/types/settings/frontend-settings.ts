import {
  BigNumber,
  Theme,
  ThemeColors,
  ThemeEnum,
  TimeFramePeriod,
  TimeFramePeriodEnum,
  TimeFramePersist,
  TimeFrameSetting,
} from '@rotki/common';
import { z } from 'zod';
import { isEmpty } from 'es-toolkit/compat';
import { Constraints, MINIMUM_DIGIT_TO_BE_ABBREVIATED } from '@/data/constraints';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { CurrencyLocationEnum } from '@/types/currency-location';
import { DateFormatEnum } from '@/types/date-format';
import { TableColumnEnum } from '@/types/table-column';
import { BaseSuggestion, SavedFilterLocation } from '@/types/filtering';
import { camelCaseTransformer } from '@/services/axios-transformers';

export const FRONTEND_SETTINGS_SCHEMA_VERSION = 1;

export enum Quarter {
  Q1 = 'Q1',
  Q2 = 'Q2',
  Q3 = 'Q3',
  Q4 = 'Q4',
  ALL = 'ALL',
}

const QuarterEnum = z.nativeEnum(Quarter);

const ProfitLossTimeframe = z.object({
  quarter: QuarterEnum,
  year: z.string(),
});

const ExplorerEndpoints = z.object({
  address: z.string().optional(),
  block: z.string().optional(),
  transaction: z.string().optional(),
});

const ExplorersSettings = z.record(z.string(), ExplorerEndpoints.optional());

const RoundingMode = z
  .number()
  .int()
  .min(0)
  .max(8)
  .transform(arg => arg as BigNumber.RoundingMode);

export type RoundingMode = z.infer<typeof RoundingMode>;

const RefreshPeriod = z.number().min(-1).max(Constraints.MAX_MINUTES_DELAY).int();

const QueryPeriod = z.number().int().max(Constraints.MAX_SECONDS_DELAY).nonnegative();

export enum DashboardTableType {
  ASSETS = 'ASSETS',
  LIABILITIES = 'LIABILITIES',
  NFT = 'NFT',
  LIQUIDITY_POSITION = 'LIQUIDITY_POSITION',
  BLOCKCHAIN_ASSET_BALANCES = 'BLOCKCHAIN_ASSET_BALANCES',
}

const DashboardTablesVisibleColumns = z.object({
  [DashboardTableType.ASSETS]: TableColumnEnum.default(Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS),
  [DashboardTableType.BLOCKCHAIN_ASSET_BALANCES]: TableColumnEnum.default(Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS),
  [DashboardTableType.LIABILITIES]: TableColumnEnum.default(Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS),
  [DashboardTableType.LIQUIDITY_POSITION]: TableColumnEnum.default(Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS),
  [DashboardTableType.NFT]: TableColumnEnum.default(Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS),
});

const VersionUpdateCheckFrequency = z.number().min(-1).max(Constraints.MAX_HOURS_DELAY).int();

export enum SupportedLanguage {
  EN = 'en',
  ES = 'es',
  GR = 'gr',
  DE = 'de',
  CN = 'cn',
  FR = 'fr',
}

const SupportedLanguageEnum = z.nativeEnum(SupportedLanguage);

export enum BlockchainRefreshButtonBehaviour {
  ONLY_REFRESH_BALANCES = 'ONLY_REFRESH_BALANCES',
  REDETECT_TOKENS = 'REDETECT_TOKENS',
}

const BlockchainRefreshButtonBehaviourEnum = z.nativeEnum(BlockchainRefreshButtonBehaviour);

const SavedFilterLocationEnum = z.nativeEnum(SavedFilterLocation);

export enum BalanceSource {
  BLOCKCHAIN = 'BLOCKCHAIN',
  EXCHANGES = 'EXCHANGES',
  MANUAL = 'MANUAL',
}

export const BalanceUsdValueThresholdV0 = z.object({
  [BalanceSource.BLOCKCHAIN]: z.string().default('0'),
  [BalanceSource.EXCHANGES]: z.string().default('0'),
  [BalanceSource.MANUAL]: z.string().default('0'),
}).optional();

export const BalanceUsdValueThresholdV1 = z.record(z.nativeEnum(BalanceSource), z.string().optional());

export type BalanceUsdValueThreshold = z.infer<typeof BalanceUsdValueThresholdV1>;

export const FrontendSettings = z.object({
  abbreviateNumber: z.boolean().default(false),
  amountRoundingMode: RoundingMode.default(BigNumber.ROUND_UP),
  balanceUsdValueThreshold: BalanceUsdValueThresholdV1.default({}),
  blockchainRefreshButtonBehaviour: BlockchainRefreshButtonBehaviourEnum.default(
    BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
  ),
  currencyLocation: CurrencyLocationEnum.default(Defaults.DEFAULT_CURRENCY_LOCATION),
  darkTheme: ThemeColors.default(DARK_COLORS),
  dashboardTablesVisibleColumns: DashboardTablesVisibleColumns.default({}),
  dateInputFormat: DateFormatEnum.default(Defaults.DEFAULT_DATE_INPUT_FORMAT),
  decimalSeparator: z.string().default(Defaults.DEFAULT_DECIMAL_SEPARATOR),
  defaultThemeVersion: z.number().default(1),
  defiSetupDone: z.boolean().default(false),
  enableAliasNames: z.boolean().default(true),
  explorers: ExplorersSettings.default({}),
  graphZeroBased: z.boolean().default(false),
  itemsPerPage: z.number().positive().int().default(10),
  language: SupportedLanguageEnum.default(SupportedLanguage.EN),
  lastKnownTimeframe: TimeFramePeriodEnum.default(TimeFramePeriod.ALL),
  lightTheme: ThemeColors.default(LIGHT_COLORS),
  minimumDigitToBeAbbreviated: z.number().default(MINIMUM_DIGIT_TO_BE_ABBREVIATED),
  nftsInNetValue: z.boolean().default(true),
  notifyNewNfts: z.boolean().optional().default(false),
  profitLossReportPeriod: ProfitLossTimeframe.default({
    quarter: Quarter.ALL,
    year: new Date().getFullYear().toString(),
  }),
  queryPeriod: z.preprocess(
    queryPeriod =>
      Math.min(Number.parseInt(queryPeriod as string) || Defaults.DEFAULT_QUERY_PERIOD, Constraints.MAX_SECONDS_DELAY),
    QueryPeriod.default(Defaults.DEFAULT_QUERY_PERIOD),
  ),
  refreshPeriod: z.preprocess(
    refreshPeriod => Math.min(Number.parseInt(refreshPeriod as string) || -1, Constraints.MAX_MINUTES_DELAY),
    RefreshPeriod.default(-1),
  ),
  renderAllNftImages: z.boolean().default(true),
  savedFilters: z
    .record(SavedFilterLocationEnum, z.array(z.array(BaseSuggestion)))
    .default({})
    // eslint-disable-next-line unicorn/prefer-top-level-await
    .catch({}),
  schemaVersion: z.literal(1),
  selectedTheme: ThemeEnum.default(Theme.AUTO),
  shouldRefreshValidatorDailyStats: z.boolean().default(false),
  showGraphRangeSelector: z.boolean().default(true),
  subscriptDecimals: z.boolean().default(false),
  thousandSeparator: z.string().default(Defaults.DEFAULT_THOUSAND_SEPARATOR),
  timeframeSetting: TimeFrameSetting.default(TimeFramePersist.REMEMBER),
  useHistoricalAssetBalances: z.boolean().default(false),
  valueRoundingMode: RoundingMode.default(BigNumber.ROUND_DOWN),
  versionUpdateCheckFrequency: z.preprocess(
    versionUpdateCheckFrequency =>
      Math.min(
        Number.parseInt(versionUpdateCheckFrequency as string) || Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY,
        Constraints.MAX_HOURS_DELAY,
      ),
    VersionUpdateCheckFrequency.default(Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY),
  ),
  visibleTimeframes: z.array(TimeFrameSetting).default(Defaults.DEFAULT_VISIBLE_TIMEFRAMES),
  whitelistedDomainsForNftImages: z.array(z.string()).default([]),
});

export type FrontendSettings = z.infer<typeof FrontendSettings>;

export type FrontendSettingsPayload = Partial<FrontendSettings>;

export function deserializeFrontendSettings<T extends object>(settings: string): T {
  return settings ? camelCaseTransformer(JSON.parse(settings)) : {};
}

export function parseFrontendSettings(settings: string): FrontendSettings {
  const data = deserializeFrontendSettings(settings);
  if (isEmpty(data)) {
    return getDefaultFrontendSettings();
  }
  return FrontendSettings.parse(data);
}

export function getDefaultFrontendSettings(props: Partial<FrontendSettings> = {}): FrontendSettings {
  return FrontendSettings.parse({
    schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
    ...props,
  });
}
