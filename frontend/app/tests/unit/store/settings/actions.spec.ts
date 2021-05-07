import { default as BigNumber } from 'bignumber.js';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  TIMEFRAME_ALL,
  TIMEFRAME_REMEMBER,
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
  DARK_MODE_ENABLED,
  LIGHT_THEME,
  DARK_THEME
} from '@/store/settings/consts';
import { FrontendSettingsPayload } from '@/store/settings/types';
import store from '@/store/store';

jest.mock('@/services/rotkehlchen-api');

describe('settings:actions', () => {
  beforeEach(() => {
    jest.resetAllMocks();
  });
  test('updates settings on valid payload', async () => {
    expect.assertions(1);
    await store.dispatch('settings/updateSetting', {
      [DEFI_SETUP_DONE]: true
    } as FrontendSettingsPayload);

    expect(api.setSettings).toHaveBeenCalledWith(
      expect.objectContaining({
        frontend_settings: JSON.stringify(
          axiosSnakeCaseTransformer({
            [DEFI_SETUP_DONE]: true,
            [TIMEFRAME_SETTING]: TIMEFRAME_REMEMBER,
            [LAST_KNOWN_TIMEFRAME]: TIMEFRAME_ALL,
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
            [DARK_THEME]: DARK_COLORS
          })
        )
      })
    );
  });

  test('does not update settings on missing payload', async () => {
    expect.assertions(1);
    await expect(
      store.dispatch('settings/updateSetting', {} as FrontendSettingsPayload)
    ).rejects.toBeInstanceOf(Error);
  });
});
