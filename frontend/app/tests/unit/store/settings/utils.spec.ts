import { BigNumber } from '@rotki/common/';
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
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD,
  PROFIT_LOSS_PERIOD,
  ALL,
  THOUSAND_SEPARATOR,
  DECIMAL_SEPARATOR,
  CURRENCY_LOCATION,
  REFRESH_PERIOD,
  EXPLORERS,
  ITEMS_PER_PAGE,
  AMOUNT_ROUNDING_MODE,
  VALUE_ROUNDING_MODE,
  GRAPH_ZERO_BASED
} from '@/store/settings/consts';
import { loadFrontendSettings } from '@/store/settings/utils';

describe('settings:utils', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });

  test('restore nothing if no valid properties are found', async () => {
    expect.assertions(1);
    const commit = jest.fn();
    loadFrontendSettings(commit, JSON.stringify({ random: 1 }));
    expect(commit).toHaveBeenCalledTimes(0);
  });

  test('restore nothing is the loaded value is not a valid json', async () => {
    expect.assertions(1);
    const commit = jest.fn();
    loadFrontendSettings(commit, 'dasda');
    expect(commit).toHaveBeenCalledTimes(0);
  });

  test('restore nothing is the loaded value has an unexpected type', async () => {
    expect.assertions(1);
    const commit = jest.fn();
    loadFrontendSettings(commit, JSON.stringify({ [DEFI_SETUP_DONE]: 1 }));
    expect(commit).toHaveBeenCalledTimes(0);
  });

  test('restore valid properties', async () => {
    expect.assertions(1);
    const commit = jest.fn();
    loadFrontendSettings(
      commit,
      JSON.stringify({ [DEFI_SETUP_DONE]: true, invalid: 2 })
    );
    expect(commit).toHaveBeenCalledWith(
      'settings/restore',
      {
        [TIMEFRAME_SETTING]: TimeFramePersist.REMEMBER,
        [DEFI_SETUP_DONE]: true,
        [LAST_KNOWN_TIMEFRAME]: TimeFramePeriod.ALL,
        [QUERY_PERIOD]: 5,
        [PROFIT_LOSS_PERIOD]: {
          year: new Date().getFullYear().toString(),
          quarter: ALL
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
        [GRAPH_ZERO_BASED]: false
      },
      { root: true }
    );
  });
});
