import { BigNumber, DARK_THEME, LIGHT_THEME, SELECTED_THEME, Theme, TimeFramePeriod, TimeFramePersist } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  BlockchainRefreshButtonBehaviour,
  FRONTEND_SETTINGS_SCHEMA_VERSION,
  FrontendSettings,
  Quarter,
  SupportedLanguage,
} from '@/types/settings/frontend-settings';

describe('settings:utils', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('restore nothing is the loaded value has an unexpected type', () => {
    expect.assertions(1);
    expect(() => FrontendSettings.parse({ defiSetupDone: 1, schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION })).toThrow();
  });

  it('restore valid properties', () => {
    expect.assertions(1);
    const frontendSettings = FrontendSettings.parse({
      defiSetupDone: true,
      invalid: 2,
      schemaVersion: FRONTEND_SETTINGS_SCHEMA_VERSION,
    });

    expect(frontendSettings).toMatchObject({
      timeframeSetting: TimeFramePersist.REMEMBER,
      defiSetupDone: true,
      language: SupportedLanguage.EN,
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
      [SELECTED_THEME]: Theme.AUTO,
      [LIGHT_THEME]: LIGHT_COLORS,
      [DARK_THEME]: DARK_COLORS,
      graphZeroBased: false,
      ignoreSnapshotError: false,
      showGraphRangeSelector: true,
      nftsInNetValue: true,
      persistTableSorting: false,
      renderAllNftImages: true,
      whitelistedDomainsForNftImages: [],
      enableAliasNames: true,
      blockchainRefreshButtonBehaviour: BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
      shouldRefreshValidatorDailyStats: false,
      showEvmQueryIndicator: true,
      savedFilters: {},
      balanceUsdValueThreshold: {},
    });
  });
});
