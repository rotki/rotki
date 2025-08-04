import { assert, BigNumber, Blockchain, Theme, TimeFramePeriod, TimeFramePersist } from '@rotki/common';
import { createPinia, type Pinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useSettingsApi } from '@/composables/api/settings/settings-api';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { camelCaseTransformer } from '@/services/axios-transformers';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import { PrivacyMode } from '@/types/session';
import {
  BalanceSource,
  BlockchainRefreshButtonBehaviour,
  DashboardTableType,
  FrontendSettings,
  Quarter,
  SupportedLanguage,
} from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn().mockResolvedValue({ other: { frontendSettings: {} } }),
  }),
}));

describe('settings:frontend', () => {
  let pinia: Pinia;
  let api: ReturnType<typeof useSettingsApi>;

  beforeEach(() => {
    pinia = createPinia();
    api = useSettingsApi();
  });

  it('updates settings on valid payload', async () => {
    expect.assertions(2);
    const store = useFrontendSettingsStore(pinia);
    await store.updateSetting({ defiSetupDone: true, language: SupportedLanguage.GR });

    expect(api.setSettings).toHaveBeenCalledOnce();
    const payload = vi.mocked(api.setSettings).mock.calls[0][0];
    assert(payload.frontendSettings);
    const parsedSettings = FrontendSettings.parse(camelCaseTransformer(JSON.parse(payload.frontendSettings)));

    expect(parsedSettings).toMatchObject({
      defiSetupDone: true,
      language: SupportedLanguage.GR,
      timeframeSetting: TimeFramePersist.REMEMBER,
      visibleTimeframes: Defaults.DEFAULT_VISIBLE_TIMEFRAMES,
      lastKnownTimeframe: TimeFramePeriod.ALL,
      queryPeriod: 5,
      profitLossReportPeriod: {
        year: new Date().getFullYear().toString(),
        quarter: Quarter.ALL,
      },
      thousandSeparator: Defaults.DEFAULT_THOUSAND_SEPARATOR,
      decimalSeparator: Defaults.DEFAULT_DECIMAL_SEPARATOR,
      currencyLocation: Defaults.DEFAULT_CURRENCY_LOCATION,
      abbreviateNumber: false,
      minimumDigitToBeAbbreviated: 4,
      refreshPeriod: -1,
      explorers: {},
      itemsPerPage: 10,
      amountRoundingMode: BigNumber.ROUND_UP,
      valueRoundingMode: BigNumber.ROUND_DOWN,
      selectedTheme: Theme.AUTO,
      lightTheme: LIGHT_COLORS,
      darkTheme: DARK_COLORS,
      defaultThemeVersion: 1,
      graphZeroBased: false,
      ignoreSnapshotError: false,
      showGraphRangeSelector: true,
      nftsInNetValue: true,
      persistTableSorting: false,
      renderAllNftImages: true,
      whitelistedDomainsForNftImages: [],
      dashboardTablesVisibleColumns: {
        [DashboardTableType.ASSETS]: Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
        [DashboardTableType.LIABILITIES]: Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
        [DashboardTableType.NFT]: Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
        [DashboardTableType.LIQUIDITY_POSITION]: Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
        [DashboardTableType.BLOCKCHAIN_ASSET_BALANCES]: Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
      },
      dateInputFormat: DateFormat.DateMonthYearHourMinuteSecond,
      versionUpdateCheckFrequency: Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY,
      enableAliasNames: true,
      blockchainRefreshButtonBehaviour: BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
      savedFilters: {},
      balanceUsdValueThreshold: {},
      persistPrivacySettings: false,
    });
  });

  it('does not update settings on missing payload', async () => {
    expect.assertions(1);
    const store = useFrontendSettingsStore(pinia);
    await expect(store.updateSetting({})).rejects.toBeInstanceOf(Error);
  });

  it('restore', () => {
    const store = useFrontendSettingsStore(pinia);
    const state: FrontendSettings = {
      schemaVersion: 1,
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
        TimeFramePeriod.WEEK,
      ],
      queryPeriod: 5,
      profitLossReportPeriod: {
        year: '2018',
        quarter: Quarter.Q3,
      },
      currencyLocation: CurrencyLocation.BEFORE,
      abbreviateNumber: false,
      minimumDigitToBeAbbreviated: 4,
      thousandSeparator: '|',
      decimalSeparator: '-',
      refreshPeriod: 120,
      notifyNewNfts: false,
      explorers: {
        [Blockchain.ETH]: {
          transaction: 'explore/tx',
        },
      },
      itemsPerPage: 25,
      valueRoundingMode: BigNumber.ROUND_DOWN,
      amountRoundingMode: BigNumber.ROUND_UP,
      selectedTheme: Theme.AUTO,
      lightTheme: {
        primary: '#000000',
        accent: '#ffffff',
        graph: '#555555',
      },
      darkTheme: {
        primary: '#ffffff',
        accent: '#000000',
        graph: '#555555',
      },
      defaultThemeVersion: 1,
      graphZeroBased: true,
      ignoreSnapshotError: false,
      showGraphRangeSelector: true,
      nftsInNetValue: true,
      persistTableSorting: false,
      renderAllNftImages: false,
      whitelistedDomainsForNftImages: [],
      dashboardTablesVisibleColumns: {
        [DashboardTableType.ASSETS]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
        [DashboardTableType.LIABILITIES]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
        [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
        [DashboardTableType.LIQUIDITY_POSITION]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
        [DashboardTableType.BLOCKCHAIN_ASSET_BALANCES]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      },
      dateInputFormat: DateFormat.DateMonthYearHourMinuteSecond,
      versionUpdateCheckFrequency: 24,
      enableAliasNames: true,
      blockchainRefreshButtonBehaviour: BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
      subscriptDecimals: false,
      savedFilters: {},
      balanceUsdValueThreshold: {
        [BalanceSource.EXCHANGES]: '0',
        [BalanceSource.BLOCKCHAIN]: '0',
        [BalanceSource.MANUAL]: '0',
      },
      useHistoricalAssetBalances: false,
      scrambleData: false,
      scrambleMultiplier: 1,
      privacyMode: PrivacyMode.NORMAL,
      persistPrivacySettings: false,
      evmQueryIndicatorMinOutOfSyncPeriod: 12,
      evmQueryIndicatorDismissalThreshold: 6,
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
      TimeFramePeriod.WEEK,
    ]);
    expect(store.queryPeriod).toBe(5);
    expect(store.profitLossReportPeriod).toMatchObject({
      year: '2018',
      quarter: Quarter.Q3,
    });
    expect(store.thousandSeparator).toBe('|');
    expect(store.decimalSeparator).toBe('-');
    expect(store.currencyLocation).toBe(CurrencyLocation.BEFORE);
    expect(store.abbreviateNumber).toBe(false);
    expect(store.minimumDigitToBeAbbreviated).toBe(4);
    expect(store.refreshPeriod).toBe(120);
    expect(store.explorers).toStrictEqual({
      [Blockchain.ETH]: {
        transaction: 'explore/tx',
      },
    });
    expect(store.itemsPerPage).toBe(25);
    expect(store.valueRoundingMode).toBe(BigNumber.ROUND_DOWN);
    expect(store.amountRoundingMode).toBe(BigNumber.ROUND_UP);
    expect(store.selectedTheme).toBe(Theme.AUTO);
    expect(store.lightTheme).toStrictEqual({
      primary: '#000000',
      accent: '#ffffff',
      graph: '#555555',
    });
    expect(store.darkTheme).toStrictEqual({
      primary: '#ffffff',
      accent: '#000000',
      graph: '#555555',
    });
    expect(store.graphZeroBased).toBe(true);
    expect(store.ignoreSnapshotError).toBe(false);
    expect(store.showGraphRangeSelector).toBe(true);
    expect(store.nftsInNetValue).toBe(true);
    expect(store.persistTableSorting).toBe(false);
    expect(store.renderAllNftImages).toBe(false);
    expect(store.whitelistedDomainsForNftImages).toStrictEqual([]);
    expect(store.dashboardTablesVisibleColumns).toStrictEqual({
      [DashboardTableType.ASSETS]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIABILITIES]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIQUIDITY_POSITION]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.BLOCKCHAIN_ASSET_BALANCES]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
    });
    expect(store.dateInputFormat).toBe(DateFormat.DateMonthYearHourMinuteSecond);
    expect(store.versionUpdateCheckFrequency).toBe(24);
    expect(store.enableAliasNames).toBe(true);
    expect(store.blockchainRefreshButtonBehaviour).toBe(BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES);
    expect(store.savedFilters).toMatchObject({});
    expect(store.persistPrivacySettings).toBe(false);
  });
});
