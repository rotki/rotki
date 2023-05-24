import { describe } from 'vitest';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { BigNumber } from '@rotki/common';
import { Theme } from '@rotki/common/lib/settings';
import { CurrencyLocation } from '@/types/currency-location';
import {
  BlockchainRefreshButtonBehaviour,
  DashboardTableType,
  type FrontendSettings,
  Quarter,
  SupportedLanguage
} from '@/types/frontend-settings';
import { TableColumn } from '@/types/table-column';
import { DateFormat } from '@/types/date-format';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { OtherSettings } from '@/types/user';

describe('types/user', () => {
  test('OtherSettings parsed correctly', () => {
    const frontendSettings: FrontendSettings = {
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
      abbreviateNumber: false,
      thousandSeparator: '|',
      decimalSeparator: '-',
      refreshPeriod: 120,
      explorers: {
        [Blockchain.ETH]: {
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
      renderAllNftImages: true,
      whitelistedDomainsForNftImages: [],
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
      enableAliasNames: true,
      blockchainRefreshButtonBehaviour:
        BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
      savedFilters: {}
    };

    const raw = {
      premiumShouldSync: true,
      havePremium: true,
      frontendSettings: JSON.stringify(snakeCaseTransformer(frontendSettings))
    };

    expect(OtherSettings.parse(raw)).toEqual({
      premiumShouldSync: true,
      havePremium: true,
      frontendSettings
    });
  });
});
