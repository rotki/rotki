import { BigNumber, Blockchain, Theme, TimeFramePeriod } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { CurrencyLocation } from '@/modules/amount-display/currency-location';
import { snakeCaseTransformer } from '@/modules/api/transformers';
import { DateFormat } from '@/modules/common/date-format';
import { PrivacyMode } from '@/modules/session/types';
import {
  BlockchainRefreshButtonBehaviour,
  DashboardTableType,
  type FrontendSettings,
  Quarter,
  SupportedLanguage,
} from '@/modules/settings/types/frontend-settings';
import { OtherSettings } from '@/modules/settings/types/user-settings';
import { TableColumn } from '@/modules/table/table-column';

describe('user-types', () => {
  it('should parse otherSettings correctly', () => {
    const frontendSettings: FrontendSettings = {
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
      notifyNewNfts: false,
      nftsInNetValue: true,
      persistTableSorting: false,
      renderAllNftImages: true,
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
      balanceValueThreshold: {},
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

    const raw = {
      premiumShouldSync: true,
      havePremium: true,
      frontendSettings: JSON.stringify(snakeCaseTransformer(frontendSettings)),
    };

    expect(OtherSettings.parse(raw)).toEqual({
      premiumShouldSync: true,
      havePremium: true,
      frontendSettings,
    });
  });
});
