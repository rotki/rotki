import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import {
  DARK_MODE_ENABLED,
  DARK_THEME,
  LIGHT_THEME,
  ThemeColors
} from '@rotki/common/lib/settings';
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

export const DEFI_SETUP_DONE = 'defiSetupDone' as const;
export const TIMEFRAME_SETTING = 'timeframeSetting' as const;
export const VISIBLE_TIMEFRAMES = 'visibleTimeframes' as const;
export const LAST_KNOWN_TIMEFRAME = 'lastKnownTimeframe' as const;
export const QUERY_PERIOD = 'queryPeriod' as const;
export const PROFIT_LOSS_PERIOD = 'profitLossReportPeriod' as const;
export const THOUSAND_SEPARATOR = 'thousandSeparator' as const;
export const DECIMAL_SEPARATOR = 'decimalSeparator' as const;
export const CURRENCY_LOCATION = 'currencyLocation' as const;
export const REFRESH_PERIOD = 'refreshPeriod' as const;
export const EXPLORERS = 'explorers' as const;
export const ITEMS_PER_PAGE = 'itemsPerPage' as const;
export const AMOUNT_ROUNDING_MODE = 'amountRoundingMode' as const;
export const VALUE_ROUNDING_MODE = 'valueRoundingMode' as const;
export const GRAPH_ZERO_BASED = 'graphZeroBased' as const;
export const NFTS_IN_NET_VALUE = 'nftsInNetValue' as const;
export const DASHBOARD_TABLES_VISIBLE_COLUMNS =
  'dashboardTablesVisibleColumns' as const;
export const DATE_INPUT_FORMAT = 'dateInputFormat' as const;
export const VERSION_UPDATE_CHECK_FREQUENCY =
  'versionUpdateCheckFrequency' as const;

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

export type QueryPeriod = z.infer<typeof RefreshPeriod>;

export enum DashboardTableType {
  ASSETS = 'ASSETS',
  LIABILITIES = 'LIABILITIES',
  NFT = 'NFT'
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

export const FrontendSettings = z.object({
  [DEFI_SETUP_DONE]: z.boolean().default(false),
  [TIMEFRAME_SETTING]: TimeFrameSetting.default(TimeFramePersist.REMEMBER),
  [VISIBLE_TIMEFRAMES]: z
    .array(TimeFrameSetting)
    .default(Defaults.DEFAULT_VISIBLE_TIMEFRAMES),
  [LAST_KNOWN_TIMEFRAME]: TimeFramePeriodEnum.default(TimeFramePeriod.ALL),
  [QUERY_PERIOD]: z.preprocess(
    queryPeriod =>
      Math.min(
        parseInt(queryPeriod as string) || Defaults.DEFAULT_QUERY_PERIOD,
        Constraints.MAX_SECONDS_DELAY
      ),
    QueryPeriod.default(Defaults.DEFAULT_QUERY_PERIOD)
  ),
  [PROFIT_LOSS_PERIOD]: ProfitLossTimeframe.default({
    year: new Date().getFullYear().toString(),
    quarter: Quarter.ALL
  }),
  [THOUSAND_SEPARATOR]: z.string().default(Defaults.DEFAULT_THOUSAND_SEPARATOR),
  [DECIMAL_SEPARATOR]: z.string().default(Defaults.DEFAULT_DECIMAL_SEPARATOR),
  [CURRENCY_LOCATION]: CurrencyLocationEnum.default(
    Defaults.DEFAULT_CURRENCY_LOCATION
  ),
  [REFRESH_PERIOD]: z.preprocess(
    refreshPeriod =>
      Math.min(
        parseInt(refreshPeriod as string) || -1,
        Constraints.MAX_MINUTES_DELAY
      ),
    RefreshPeriod.default(-1)
  ),
  [EXPLORERS]: ExplorersSettings.default({}),
  [ITEMS_PER_PAGE]: z.number().positive().int().default(10),
  [AMOUNT_ROUNDING_MODE]: RoundingMode.default(BigNumber.ROUND_UP),
  [VALUE_ROUNDING_MODE]: RoundingMode.default(BigNumber.ROUND_DOWN),
  [DARK_MODE_ENABLED]: z.boolean().default(false),
  [LIGHT_THEME]: ThemeColors.default(LIGHT_COLORS),
  [DARK_THEME]: ThemeColors.default(DARK_COLORS),
  [GRAPH_ZERO_BASED]: z.boolean().default(false),
  [NFTS_IN_NET_VALUE]: z.boolean().default(true),
  [DASHBOARD_TABLES_VISIBLE_COLUMNS]: DashboardTablesVisibleColumns.default({}),
  [DATE_INPUT_FORMAT]: DateFormatEnum.default(
    Defaults.DEFAULT_DATE_INPUT_FORMAT
  ),
  [VERSION_UPDATE_CHECK_FREQUENCY]: z.preprocess(
    versionUpdateCheckFrequency =>
      Math.min(
        parseInt(versionUpdateCheckFrequency as string) ||
          Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY,
        Constraints.MAX_HOURS_DELAY
      ),
    VersionUpdateCheckFrequency.default(
      Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY
    )
  )
});

export type FrontendSettings = z.infer<typeof FrontendSettings>;
export type FrontendSettingsPayload = Partial<FrontendSettings>;
