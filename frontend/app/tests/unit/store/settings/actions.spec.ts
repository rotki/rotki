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
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import store from '@/store/store';
import { DateFormat } from '@/types/date-format';
import {
  AMOUNT_ROUNDING_MODE,
  CURRENCY_LOCATION,
  DASHBOARD_TABLES_VISIBLE_COLUMNS,
  DashboardTableType,
  DATE_INPUT_FORMAT,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  EXPLORERS,
  FrontendSettingsPayload,
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
  VALUE_ROUNDING_MODE,
  VERSION_UPDATE_CHECK_FREQUENCY,
  VISIBLE_TIMEFRAMES
} from '@/types/frontend-settings';

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
        frontendSettings: JSON.stringify(
          axiosSnakeCaseTransformer({
            [DEFI_SETUP_DONE]: true,
            [TIMEFRAME_SETTING]: TimeFramePersist.REMEMBER,
            [VISIBLE_TIMEFRAMES]: Defaults.DEFAULT_VISIBLE_TIMEFRAMES,
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
            [NFTS_IN_NET_VALUE]: true,
            [DASHBOARD_TABLES_VISIBLE_COLUMNS]: {
              [DashboardTableType.ASSETS]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
              [DashboardTableType.LIABILITIES]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS,
              [DashboardTableType.NFT]:
                Defaults.DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS
            },
            [DATE_INPUT_FORMAT]: DateFormat.DateMonthYearHourMinuteSecond,
            [VERSION_UPDATE_CHECK_FREQUENCY]:
              Defaults.DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY
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
