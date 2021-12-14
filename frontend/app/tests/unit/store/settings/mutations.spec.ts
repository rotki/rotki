import { BigNumber } from '@rotki/common';
import {
  DARK_MODE_ENABLED,
  DARK_THEME,
  LIGHT_THEME
} from '@rotki/common/lib/settings';
import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { SettingsState } from '@/store/settings/state';
import store from '@/store/store';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import { TableColumn } from '@/types/table-column';
import {
  AMOUNT_ROUNDING_MODE,
  CURRENCY_LOCATION,
  DASHBOARD_TABLES_VISIBLE_COLUMNS,
  DashboardTableType,
  DATE_INPUT_FORMAT,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  EXPLORERS,
  GRAPH_ZERO_BASED,
  ITEMS_PER_PAGE,
  LAST_KNOWN_TIMEFRAME,
  NFTS_IN_NET_VALUE,
  PROFIT_LOSS_PERIOD,
  Quarter,
  QUERY_PERIOD,
  REFRESH_PERIOD,
  THOUSAND_SEPARATOR,
  TIMEFRAME_SETTING,
  VALUE_ROUNDING_MODE,
  VERSION_UPDATE_CHECK_FREQUENCY,
  VISIBLE_TIMEFRAMES
} from '../../../../src/types/frontend-settings';

describe('settings:mutations', () => {
  test('restore', async () => {
    const state: SettingsState = {
      [DEFI_SETUP_DONE]: true,
      [TIMEFRAME_SETTING]: TimeFramePeriod.YEAR,
      [LAST_KNOWN_TIMEFRAME]: TimeFramePeriod.TWO_WEEKS,
      [VISIBLE_TIMEFRAMES]: [
        TimeFramePeriod.ALL,
        TimeFramePeriod.YEAR,
        TimeFramePeriod.THREE_MONTHS,
        TimeFramePeriod.MONTH,
        TimeFramePeriod.TWO_WEEKS,
        TimeFramePeriod.WEEK
      ],
      [QUERY_PERIOD]: 5,
      [PROFIT_LOSS_PERIOD]: {
        year: '2018',
        quarter: Quarter.Q3
      },
      [CURRENCY_LOCATION]: CurrencyLocation.BEFORE,
      [THOUSAND_SEPARATOR]: '|',
      [DECIMAL_SEPARATOR]: '-',
      [REFRESH_PERIOD]: 120,
      [EXPLORERS]: {
        ETH: {
          transaction: 'explore/tx'
        }
      },
      [ITEMS_PER_PAGE]: 25,
      [VALUE_ROUNDING_MODE]: BigNumber.ROUND_DOWN,
      [AMOUNT_ROUNDING_MODE]: BigNumber.ROUND_UP,
      [DARK_MODE_ENABLED]: true,
      [LIGHT_THEME]: {
        primary: '#000000',
        accent: '#ffffff',
        graph: '#555555'
      },
      [DARK_THEME]: {
        primary: '#ffffff',
        accent: '#000000',
        graph: '#555555'
      },
      [GRAPH_ZERO_BASED]: true,
      [NFTS_IN_NET_VALUE]: true,
      [DASHBOARD_TABLES_VISIBLE_COLUMNS]: {
        [DashboardTableType.ASSETS]: [
          TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
        ],
        [DashboardTableType.LIABILITIES]: [
          TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
        ],
        [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE]
      },
      [DATE_INPUT_FORMAT]: DateFormat.DateMonthYearHourMinuteSecond,
      [VERSION_UPDATE_CHECK_FREQUENCY]: 24
    };
    store.commit('settings/restore', state);
    const settings = store.state.settings!;
    expect(settings[DEFI_SETUP_DONE]).toBe(true);
    expect(settings[TIMEFRAME_SETTING]).toBe(TimeFramePeriod.YEAR);
    expect(settings[LAST_KNOWN_TIMEFRAME]).toBe(TimeFramePeriod.TWO_WEEKS);
    expect(settings[VISIBLE_TIMEFRAMES]).toStrictEqual([
      TimeFramePeriod.ALL,
      TimeFramePeriod.YEAR,
      TimeFramePeriod.THREE_MONTHS,
      TimeFramePeriod.MONTH,
      TimeFramePeriod.TWO_WEEKS,
      TimeFramePeriod.WEEK
    ]);
    expect(settings[QUERY_PERIOD]).toBe(5);
    expect(settings[PROFIT_LOSS_PERIOD]).toMatchObject({
      year: '2018',
      quarter: Quarter.Q3
    });
    expect(settings[THOUSAND_SEPARATOR]).toBe('|');
    expect(settings[DECIMAL_SEPARATOR]).toBe('-');
    expect(settings[CURRENCY_LOCATION]).toBe(CurrencyLocation.BEFORE);
    expect(settings[REFRESH_PERIOD]).toBe(120);
    expect(settings[EXPLORERS]).toStrictEqual({
      ETH: {
        transaction: 'explore/tx'
      }
    });
    expect(settings[ITEMS_PER_PAGE]).toBe(25);
    expect(settings[VALUE_ROUNDING_MODE]).toBe(BigNumber.ROUND_DOWN);
    expect(settings[AMOUNT_ROUNDING_MODE]).toBe(BigNumber.ROUND_UP);
    expect(settings[DARK_MODE_ENABLED]).toBe(true);
    expect(settings[LIGHT_THEME]).toStrictEqual({
      primary: '#000000',
      accent: '#ffffff',
      graph: '#555555'
    });
    expect(settings[DARK_THEME]).toStrictEqual({
      primary: '#ffffff',
      accent: '#000000',
      graph: '#555555'
    });
    expect(settings[GRAPH_ZERO_BASED]).toBe(true);
    expect(settings[NFTS_IN_NET_VALUE]).toBe(true);
    expect(settings[DASHBOARD_TABLES_VISIBLE_COLUMNS]).toStrictEqual({
      [DashboardTableType.ASSETS]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIABILITIES]: [
        TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
      ],
      [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE]
    });
    expect(settings[DATE_INPUT_FORMAT]).toBe(
      DateFormat.DateMonthYearHourMinuteSecond
    );
    expect(settings[VERSION_UPDATE_CHECK_FREQUENCY]).toBe(24);
  });
});
