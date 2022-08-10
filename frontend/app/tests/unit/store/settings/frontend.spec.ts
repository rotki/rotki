import { BigNumber } from '@rotki/common';
import { Theme } from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePersist
} from '@rotki/common/lib/settings/graphs';
import { createPinia, Pinia } from 'pinia';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import {
  DashboardTableType,
  FrontendSettings,
  Quarter,
  SupportedLanguage
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';

vi.mock('@/services/rotkehlchen-api');

describe('settings:frontend', () => {
  let pinia: Pinia;
  beforeEach(() => {
    vi.resetAllMocks();
    pinia = createPinia();
  });

  test('updates settings on valid payload', async () => {
    expect.assertions(1);
    const store = useFrontendSettingsStore(pinia);
    await store.updateSetting({ defiSetupDone: true });

    expect(api.setSettings).toHaveBeenCalledWith(
      expect.objectContaining({
        frontendSettings: JSON.stringify(
          axiosSnakeCaseTransformer({
            defiSetupDone: true,
            language: SupportedLanguage.EN,
            timeframeSetting: TimeFramePersist.REMEMBER,
            visibleTimeframes: Defaults.DEFAULT_VISIBLE_TIMEFRAMES,
            lastKnownTimeframe: TimeFramePeriod.ALL,
            queryPeriod: 5,
            profitLossReportPeriod: {
              year: new Date().getFullYear().toString(),
              quarter: Quarter.ALL
            },
            thousandSeparator: Defaults.DEFAULT_THOUSAND_SEPARATOR,
            decimalSeparator: Defaults.DEFAULT_DECIMAL_SEPARATOR,
            currencyLocation: Defaults.DEFAULT_CURRENCY_LOCATION,
            refreshPeriod: -1,
            explorers: {},
            itemsPerPage: 10,
            amountRoundingMode: BigNumber.ROUND_UP,
            valueRoundingMode: BigNumber.ROUND_DOWN,
            selectedTheme: Theme.AUTO,
            lightTheme: LIGHT_COLORS,
            darkTheme: DARK_COLORS,
            graphZeroBased: false,
            showGraphRangeSelector: true,
            nftsInNetValue: true,
            dashboardTablesVisibleColumns: {
              [DashboardTableType.ASSETS]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
              [DashboardTableType.LIABILITIES]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
              [DashboardTableType.NFT]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
              [DashboardTableType.LIQUIDITY_POSITION]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS
            },
            dateInputFormat: DateFormat.DateMonthYearHourMinuteSecond,
            versionUpdateCheckFrequency:
              Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY,
            enableEthNames: true
          })
        )
      })
    );
  });

  test('does not update settings on missing payload', async () => {
    expect.assertions(1);
    const store = useFrontendSettingsStore(pinia);
    await expect(store.updateSetting({})).rejects.toBeInstanceOf(Error);
  });

  test('restore', async () => {
    const store = useFrontendSettingsStore(pinia);
    const state: FrontendSettings = {
      defiSetupDone: true,
      language: SupportedLanguage.EN,
      timeframeSetting: TimeFramePeriod.YEAR,
      lastKnownTimeframe: TimeFramePeriod.TWO_WEEKS,
      visibleTimeframes: [
        TimeFramePeriod.ALL,
        TimeFramePeriod.YEAR,
        TimeFramePeriod.THREE_MONTHS,
        TimeFramePeriod.MONTH,
        TimeFramePeriod.TWO_WEEKS,
        TimeFramePeriod.WEEK
      ],
      queryPeriod: 5,
      profitLossReportPeriod: {
        year: '2018',
        quarter: Quarter.Q3
      },
      currencyLocation: CurrencyLocation.BEFORE,
      thousandSeparator: '|',
      decimalSeparator: '-',
      refreshPeriod: 120,
      explorers: {
        ETH: {
          transaction: 'explore/tx'
        }
      },
      itemsPerPage: 25,
      valueRoundingMode: BigNumber.ROUND_DOWN,
      amountRoundingMode: BigNumber.ROUND_UP,
      selectedTheme: Theme.AUTO,
      lightTheme: {
        primary: '#000000',
        accent: '#ffffff',
        graph: '#555555'
      },
      darkTheme: {
        primary: '#ffffff',
        accent: '#000000',
        graph: '#555555'
      },
      graphZeroBased: true,
      showGraphRangeSelector: true,
      nftsInNetValue: true,
      dashboardTablesVisibleColumns: {
        [DashboardTableType.ASSETS]: [
          TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
        ],
        [DashboardTableType.LIABILITIES]: [
          TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
        ],
        [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
        [DashboardTableType.LIQUIDITY_POSITION]: [
          TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
        ]
      },
      dateInputFormat: DateFormat.DateMonthYearHourMinuteSecond,
      versionUpdateCheckFrequency: 24,
      enableEthNames: true
    };

    store.update(state);

    expect(store.defiSetupDone).toBe(true);
    expect(store.language).toBe(SupportedLanguage.EN);
    expect(store.timeframeSetting).toBe(TimeFramePeriod.YEAR);
    expect(store.lastKnownTimeframe).toBe(TimeFramePeriod.TWO_WEEKS);
    expect(store.visibleTimeframes).toStrictEqual([
      TimeFramePeriod.ALL,
      TimeFramePeriod.YEAR,
      TimeFramePeriod.THREE_MONTHS,
      TimeFramePeriod.MONTH,
      TimeFramePeriod.TWO_WEEKS,
      TimeFramePeriod.WEEK
    ]);
    expect(store.queryPeriod).toBe(5);
    expect(store.profitLossReportPeriod).toMatchObject({
      year: '2018',
      quarter: Quarter.Q3
    });
    expect(store.thousandSeparator).toBe('|');
    expect(store.decimalSeparator).toBe('-');
    expect(store.currencyLocation).toBe(CurrencyLocation.BEFORE);
    expect(store.refreshPeriod).toBe(120);
    expect(store.explorers).toStrictEqual({
      ETH: {
        transaction: 'explore/tx'
      }
    });
    expect(store.itemsPerPage).toBe(25);
    expect(store.valueRoundingMode).toBe(BigNumber.ROUND_DOWN);
    expect(store.amountRoundingMode).toBe(BigNumber.ROUND_UP);
    expect(store.selectedTheme).toBe(Theme.AUTO);
    expect(store.lightTheme).toStrictEqual({
      primary: '#000000',
      accent: '#ffffff',
      graph: '#555555'
    });
    expect(store.darkTheme).toStrictEqual({
      primary: '#ffffff',
      accent: '#000000',
      graph: '#555555'
    });
    expect(store.graphZeroBased).toBe(true);
    expect(store.showGraphRangeSelector).toBe(true);
    expect(store.nftsInNetValue).toBe(true);
    expect(store.dashboardTablesVisibleColumns).toStrictEqual({
      [DashboardTableType.ASSETS]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIABILITIES]: [
        TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
      ],
      [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIQUIDITY_POSITION]: [
        TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
      ]
    });
    expect(store.dateInputFormat).toBe(
      DateFormat.DateMonthYearHourMinuteSecond
    );
    expect(store.versionUpdateCheckFrequency).toBe(24);
    expect(store.enableEthNames).toBe(true);
  });
});
