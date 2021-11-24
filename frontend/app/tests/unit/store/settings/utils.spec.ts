import { BigNumber } from '@rotki/common';
import {
  DARK_MODE_ENABLED,
  DARK_THEME,
  LIGHT_THEME
} from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFramePersist
} from '@rotki/common/lib/settings/graphs';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  AMOUNT_ROUNDING_MODE,
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  EXPLORERS,
  FrontendSettings,
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
  VALUE_ROUNDING_MODE
} from '@/types/frontend-settings';

describe('settings:utils', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  test('restore nothing is the loaded value has an unexpected type', async () => {
    expect.assertions(1);
    expect(() => FrontendSettings.parse({ [DEFI_SETUP_DONE]: 1 })).toThrow();
  });

  test('restore valid properties', async () => {
    expect.assertions(1);
    const frontendSettings = FrontendSettings.parse({
      [DEFI_SETUP_DONE]: true,
      invalid: 2
    });

    expect(frontendSettings).toMatchObject({
      [TIMEFRAME_SETTING]: TimeFramePersist.REMEMBER,
      [DEFI_SETUP_DONE]: true,
      [LAST_KNOWN_TIMEFRAME]: TimeFramePeriod.ALL,
      [QUERY_PERIOD]: 5,
      [PROFIT_LOSS_PERIOD]: {
        year: new Date().getFullYear().toString(),
        quarter: Quarter.ALL
      },
      [THOUSAND_SEPARATOR]: Defaults.DEFAULT_THOUSAND_SEPARATOR,
      [DECIMAL_SEPARATOR]: Defaults.DEFAULT_DECIMAL_SEPARATOR,
      [CURRENCY_LOCATION]: Defaults.DEFAULT_CURRENCY_LOCATION,
      [REFRESH_PERIOD]: -1,
      [EXPLORERS]: {},
      [ITEMS_PER_PAGE]: 10,
      [AMOUNT_ROUNDING_MODE]: BigNumber.ROUND_UP,
      [VALUE_ROUNDING_MODE]: BigNumber.ROUND_DOWN,
      [DARK_MODE_ENABLED]: false,
      [LIGHT_THEME]: LIGHT_COLORS,
      [DARK_THEME]: DARK_COLORS,
      [GRAPH_ZERO_BASED]: false,
      [NFTS_IN_NET_VALUE]: true
    });
  });
});
