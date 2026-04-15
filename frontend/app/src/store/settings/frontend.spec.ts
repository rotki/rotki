import { BigNumber, Blockchain, Theme, TimeFramePeriod } from '@rotki/common';
import { createPinia, type Pinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { CurrencyLocation } from '@/modules/amount-display/currency-location';
import { DateFormat } from '@/modules/common/date-format';
import { PrivacyMode } from '@/modules/session/types';
import {
  BalanceSource,
  BlockchainRefreshButtonBehaviour,
  DashboardTableType,
  type FrontendSettings,
  Quarter,
  SupportedLanguage,
} from '@/modules/settings/types/frontend-settings';
import { TableColumn } from '@/modules/table/table-column';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

describe('useFrontendSettingsStore', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
  });

  it('should update store state via update()', () => {
    const store = useFrontendSettingsStore(pinia);
    store.update({ defiSetupDone: true, language: SupportedLanguage.GR });

    expect(store.defiSetupDone).toBe(true);
    expect(store.language).toBe(SupportedLanguage.GR);
  });

  it('should restore settings', () => {
    const store = useFrontendSettingsStore(pinia);
    const state: FrontendSettings = {
      schemaVersion: 2,
      defiSetupDone: true,
      language: SupportedLanguage.EN,
      lastAppliedSettingsVersion: '0.0.0',
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
      queryPeriod: 15,
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
      enablePasswordConfirmation: true,
      blockchainRefreshButtonBehaviour: BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
      subscriptDecimals: false,
      savedFilters: {},
      balanceValueThreshold: {
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
      lastPasswordConfirmed: 0,
      passwordConfirmationInterval: 604800,
      newlyDetectedTokensMaxCount: 500,
      newlyDetectedTokensTtlDays: 30,
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
    expect(store.queryPeriod).toBe(15);
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
    expect(store.blockchainRefreshButtonBehaviour).toBe(
      BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
    );
    expect(store.savedFilters).toMatchObject({});
    expect(store.persistPrivacySettings).toBe(false);
  });
});
