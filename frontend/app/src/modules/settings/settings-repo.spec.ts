import { BigNumber, Blockchain, Theme, TimeFramePeriod } from '@rotki/common';
import { createPinia, type Pinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { CurrencyLocation } from '@/modules/assets/amount-display/currency-location';
import { DateFormat } from '@/modules/core/common/date-format';
import { TableColumn } from '@/modules/core/table/table-column';
import { PrivacyMode } from '@/modules/session/types';
import { useAnimationsEnabled } from '@/modules/session/use-animations-enabled';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import {
  BalanceSource,
  BlockchainRefreshButtonBehaviour,
  DashboardTableType,
  type FrontendSettings,
  Quarter,
  SupportedLanguage,
} from '@/modules/settings/types/frontend-settings';

describe('useSettingsRepo frontend channel', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
  });

  it('should update store state via update()', () => {
    const store = useSettingsRepo(pinia);
    store.updateFrontend({ defiSetupDone: true, language: SupportedLanguage.GR });

    expect(store.frontend.defiSetupDone).toBe(true);
    expect(store.frontend.language).toBe(SupportedLanguage.GR);
  });

  it('should default suppressNoIndexerChains to an empty array', () => {
    const store = useSettingsRepo(pinia);
    expect(get(store.frontend.suppressNoIndexerChains)).toEqual([]);
  });

  it('should default autoDetectTokensCooldownHours to 24', () => {
    const store = useSettingsRepo(pinia);
    expect(get(store.frontend.autoDetectTokensCooldownHours)).toBe(24);
  });

  it('should default lastAutoDetectAt to 0', () => {
    const store = useSettingsRepo(pinia);
    expect(get(store.frontend.lastAutoDetectAt)).toBe(0);
  });

  it('should restore settings', () => {
    const store = useSettingsRepo(pinia);
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
      suppressNoIndexerChains: [],
      autoDetectTokensCooldownHours: 24,
      autoDetectTokensOnLogin: false,
      lastAutoDetectAt: 0,
      gnosisPaySafeMigrationLastNotified: 0,
      gnosisPaySafeMigrationNeverNotify: false,
    };

    store.updateFrontend(state);

    expect(store.frontend.defiSetupDone).toBe(true);
    expect(store.frontend.language).toBe(SupportedLanguage.EN);
    expect(store.frontend.timeframeSetting).toBe(TimeFramePeriod.YEAR);
    expect(store.frontend.lastKnownTimeframe).toBe(TimeFramePeriod.TWO_WEEKS);
    expect(store.frontend.visibleTimeframes).toStrictEqual([
      TimeFramePeriod.ALL,
      TimeFramePeriod.YEAR,
      TimeFramePeriod.THREE_MONTHS,
      TimeFramePeriod.MONTH,
      TimeFramePeriod.TWO_WEEKS,
      TimeFramePeriod.WEEK,
    ]);
    expect(store.frontend.queryPeriod).toBe(15);
    expect(store.frontend.profitLossReportPeriod).toMatchObject({
      year: '2018',
      quarter: Quarter.Q3,
    });
    expect(store.frontend.thousandSeparator).toBe('|');
    expect(store.frontend.decimalSeparator).toBe('-');
    expect(store.frontend.currencyLocation).toBe(CurrencyLocation.BEFORE);
    expect(store.frontend.abbreviateNumber).toBe(false);
    expect(store.frontend.minimumDigitToBeAbbreviated).toBe(4);
    expect(store.frontend.refreshPeriod).toBe(120);
    expect(store.frontend.explorers).toStrictEqual({
      [Blockchain.ETH]: {
        transaction: 'explore/tx',
      },
    });
    expect(store.frontend.itemsPerPage).toBe(25);
    expect(store.frontend.valueRoundingMode).toBe(BigNumber.ROUND_DOWN);
    expect(store.frontend.amountRoundingMode).toBe(BigNumber.ROUND_UP);
    expect(store.frontend.selectedTheme).toBe(Theme.AUTO);
    expect(store.frontend.lightTheme).toStrictEqual({
      primary: '#000000',
      accent: '#ffffff',
      graph: '#555555',
    });
    expect(store.frontend.darkTheme).toStrictEqual({
      primary: '#ffffff',
      accent: '#000000',
      graph: '#555555',
    });
    expect(store.frontend.graphZeroBased).toBe(true);
    expect(store.frontend.ignoreSnapshotError).toBe(false);
    expect(store.frontend.showGraphRangeSelector).toBe(true);
    expect(store.frontend.nftsInNetValue).toBe(true);
    expect(store.frontend.persistTableSorting).toBe(false);
    expect(store.frontend.renderAllNftImages).toBe(false);
    expect(store.frontend.whitelistedDomainsForNftImages).toStrictEqual([]);
    expect(store.frontend.dashboardTablesVisibleColumns).toStrictEqual({
      [DashboardTableType.ASSETS]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIABILITIES]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.NFT]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.LIQUIDITY_POSITION]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
      [DashboardTableType.BLOCKCHAIN_ASSET_BALANCES]: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE],
    });
    expect(store.frontend.dateInputFormat).toBe(DateFormat.DateMonthYearHourMinuteSecond);
    expect(store.frontend.versionUpdateCheckFrequency).toBe(24);
    expect(store.frontend.enableAliasNames).toBe(true);
    expect(store.frontend.blockchainRefreshButtonBehaviour).toBe(
      BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
    );
    expect(store.frontend.savedFilters).toMatchObject({});
    expect(store.frontend.persistPrivacySettings).toBe(false);
  });
});

describe('useSettingsRepo registry effects and mirrors', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createPinia();
  });

  it('should reconfigure the BigNumber format when the separators change', () => {
    const store = useSettingsRepo(pinia);

    store.updateFrontend({ decimalSeparator: '-', thousandSeparator: '|' });

    // the thousandSeparator/decimalSeparator effect runs applyBigNumberFormat post-persist
    expect(new BigNumber(1234567.89).toFormat()).toBe('1|234|567-89');
  });

  it('should not re-run the separator effect when those keys are unchanged', () => {
    const store = useSettingsRepo(pinia);
    store.updateFrontend({ decimalSeparator: '.', thousandSeparator: ',' });

    // an update that does not touch the separators must leave the format intact
    store.updateFrontend({ language: SupportedLanguage.GR });

    expect(new BigNumber(1234567.89).toFormat()).toBe('1,234,567.89');
  });

  it('should sync the itemsPerPage mirror ref when itemsPerPage changes', () => {
    const itemsPerPage = useItemsPerPage();
    set(itemsPerPage, 10);
    const store = useSettingsRepo(pinia);

    store.updateFrontend({ itemsPerPage: 25 });

    expect(get(itemsPerPage)).toBe(25);
  });

  it('should leave the itemsPerPage mirror untouched when itemsPerPage is not in the patch', () => {
    const itemsPerPage = useItemsPerPage();
    set(itemsPerPage, 99);
    const store = useSettingsRepo(pinia);

    store.updateFrontend({ language: SupportedLanguage.GR });

    expect(get(itemsPerPage)).toBe(99);
  });

  it('should sync the animationsEnabled mirror (localStorage) when it changes via the session channel', () => {
    const animationsEnabled = useAnimationsEnabled();
    set(animationsEnabled, true);
    const store = useSettingsRepo(pinia);

    store.updateSession({ animationsEnabled: false });

    expect(get(animationsEnabled)).toBe(false);
  });
});
