import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Theme, ThemeColors, ThemeEnum } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePeriodEnum,
  TimeFramePersist,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { z } from 'zod';
import { Constraints } from '@/data/constraints';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { CurrencyLocationEnum } from '@/types/currency-location';
import { DateFormatEnum } from '@/types/date-format';
import { TableColumnEnum } from '@/types/table-column';

export enum Quarter {
  Q1 = 'Q1',
  Q2 = 'Q2',
  Q3 = 'Q3',
  Q4 = 'Q4',
  ALL = 'ALL'
}

const QuarterEnum = z.nativeEnum(Quarter);

const ProfitLossTimeframe = z.object({
  year: z.string(),
  quarter: QuarterEnum
});

export type ProfitLossTimeframe = z.infer<typeof ProfitLossTimeframe>;

const ExplorerEndpoints = z.object({
  transaction: z.string().optional(),
  address: z.string().optional()
});

const ExplorersSettings = z.object({
  ETC: ExplorerEndpoints.optional(),
  [Blockchain.ETH]: ExplorerEndpoints.optional(),
  [Blockchain.ETH2]: ExplorerEndpoints.optional(),
  [Blockchain.BTC]: ExplorerEndpoints.optional(),
  [Blockchain.BCH]: ExplorerEndpoints.optional(),
  [Blockchain.KSM]: ExplorerEndpoints.optional(),
  [Blockchain.DOT]: ExplorerEndpoints.optional(),
  [Blockchain.AVAX]: ExplorerEndpoints.optional()
});

export type ExplorersSettings = z.infer<typeof ExplorersSettings>;

const RoundingMode = z
  .number()
  .int()
  .min(0)
  .max(8)
  .transform(arg => arg as BigNumber.RoundingMode);

export type RoundingMode = z.infer<typeof RoundingMode>;

const RefreshPeriod = z
  .number()
  .min(-1)
  .max(Constraints.MAX_MINUTES_DELAY)
  .int();

export type RefreshPeriod = z.infer<typeof RefreshPeriod>;

const QueryPeriod = z
  .number()
  .int()
  .max(Constraints.MAX_SECONDS_DELAY)
  .nonnegative();

export enum DashboardTableType {
  ASSETS = 'ASSETS',
  LIABILITIES = 'LIABILITIES',
  NFT = 'NFT',
  LIQUIDITY_POSITION = 'LIQUIDITY_POSITION'
}

const DashboardTablesVisibleColumns = z.object({
  [DashboardTableType.ASSETS]: TableColumnEnum.default(
    Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS
  ),
  [DashboardTableType.LIABILITIES]: TableColumnEnum.default(
    Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS
  ),
  [DashboardTableType.NFT]: TableColumnEnum.default(
    Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS
  ),
  [DashboardTableType.LIQUIDITY_POSITION]: TableColumnEnum.default(
    Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS
  )
});

export type DashboardTablesVisibleColumns = z.infer<
  typeof DashboardTablesVisibleColumns
>;

const VersionUpdateCheckFrequency = z
  .number()
  .min(-1)
  .max(Constraints.MAX_HOURS_DELAY)
  .int();

export type VersionUpdateCheckFrequency = z.infer<
  typeof VersionUpdateCheckFrequency
>;

export enum SupportedLanguage {
  EN = 'en',
  ES = 'es'
}

const SupportedLanguageEnum = z.nativeEnum(SupportedLanguage);

export const FrontendSettings = z.object({
  defiSetupDone: z.boolean().default(false),
  language: SupportedLanguageEnum.default(SupportedLanguage.EN),
  timeframeSetting: TimeFrameSetting.default(TimeFramePersist.REMEMBER),
  visibleTimeframes: z
    .array(TimeFrameSetting)
    .default(Defaults.DEFAULT_VISIBLE_TIMEFRAMES),
  lastKnownTimeframe: TimeFramePeriodEnum.default(TimeFramePeriod.ALL),
  queryPeriod: z.preprocess(
    queryPeriod =>
      Math.min(
        parseInt(queryPeriod as string) || Defaults.DEFAULT_QUERY_PERIOD,
        Constraints.MAX_SECONDS_DELAY
      ),
    QueryPeriod.default(Defaults.DEFAULT_QUERY_PERIOD)
  ),
  profitLossReportPeriod: ProfitLossTimeframe.default({
    year: new Date().getFullYear().toString(),
    quarter: Quarter.ALL
  }),
  thousandSeparator: z.string().default(Defaults.DEFAULT_THOUSAND_SEPARATOR),
  decimalSeparator: z.string().default(Defaults.DEFAULT_DECIMAL_SEPARATOR),
  currencyLocation: CurrencyLocationEnum.default(
    Defaults.DEFAULT_CURRENCY_LOCATION
  ),
  refreshPeriod: z.preprocess(
    refreshPeriod =>
      Math.min(
        parseInt(refreshPeriod as string) || -1,
        Constraints.MAX_MINUTES_DELAY
      ),
    RefreshPeriod.default(-1)
  ),
  explorers: ExplorersSettings.default({}),
  itemsPerPage: z.number().positive().int().default(10),
  amountRoundingMode: RoundingMode.default(BigNumber.ROUND_UP),
  valueRoundingMode: RoundingMode.default(BigNumber.ROUND_DOWN),
  selectedTheme: ThemeEnum.default(Theme.AUTO),
  lightTheme: ThemeColors.default(LIGHT_COLORS),
  darkTheme: ThemeColors.default(DARK_COLORS),
  graphZeroBased: z.boolean().default(false),
  showGraphRangeSelector: z.boolean().default(true),
  nftsInNetValue: z.boolean().default(true),
  dashboardTablesVisibleColumns: DashboardTablesVisibleColumns.default({}),
  dateInputFormat: DateFormatEnum.default(Defaults.DEFAULT_DATE_INPUT_FORMAT),
  versionUpdateCheckFrequency: z.preprocess(
    versionUpdateCheckFrequency =>
      Math.min(
        parseInt(versionUpdateCheckFrequency as string) ||
          Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY,
        Constraints.MAX_HOURS_DELAY
      ),
    VersionUpdateCheckFrequency.default(
      Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY
    )
  ),
  enableEthNames: z.boolean().default(true)
});

export type FrontendSettings = z.infer<typeof FrontendSettings>;
export type FrontendSettingsPayload = Partial<FrontendSettings>;
