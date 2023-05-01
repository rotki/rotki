import { BigNumber } from '@rotki/common';
import {
  DARK_THEME,
  LIGHT_THEME,
  SELECTED_THEME,
  Theme
} from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePersist
} from '@rotki/common/lib/settings/graphs';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  BlockchainRefreshButtonBehaviour,
  FrontendSettings,
  Quarter,
  SupportedLanguage
} from '@/types/frontend-settings';

describe('settings:utils', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  test('restore nothing is the loaded value has an unexpected type', async () => {
    expect.assertions(1);
    expect(() => FrontendSettings.parse({ defiSetupDone: 1 })).toThrow();
  });

  test('restore valid properties', async () => {
    expect.assertions(1);
    const frontendSettings = FrontendSettings.parse({
      defiSetupDone: true,
      invalid: 2
    });

    expect(frontendSettings).toMatchObject({
      timeframeSetting: TimeFramePersist.REMEMBER,
      defiSetupDone: true,
      language: SupportedLanguage.EN,
      lastKnownTimeframe: TimeFramePeriod.ALL,
      queryPeriod: 5,
      profitLossReportPeriod: {
        year: new Date().getFullYear().toString(),
        quarter: Quarter.ALL
      },
      thousandSeparator: Defaults.DEFAULT_THOUSAND_SEPARATOR,
      decimalSeparator: Defaults.DEFAULT_DECIMAL_SEPARATOR,
      currencyLocation: Defaults.DEFAULT_CURRENCY_LOCATION,
      abbreviateNumber: false,
      refreshPeriod: -1,
      explorers: {},
      itemsPerPage: 10,
      amountRoundingMode: BigNumber.ROUND_UP,
      valueRoundingMode: BigNumber.ROUND_DOWN,
      [SELECTED_THEME]: Theme.AUTO,
      [LIGHT_THEME]: LIGHT_COLORS,
      [DARK_THEME]: DARK_COLORS,
      graphZeroBased: false,
      showGraphRangeSelector: true,
      nftsInNetValue: true,
      renderAllNftImages: true,
      whitelistedDomainsForNftImages: [],
      enableAliasNames: true,
      blockchainRefreshButtonBehaviour:
        BlockchainRefreshButtonBehaviour.ONLY_REFRESH_BALANCES,
      savedFilters: {}
    });
  });
});
