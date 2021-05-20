import { default as BigNumber } from 'bignumber.js';
import {
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  LAST_KNOWN_TIMEFRAME,
  Q3,
  QUERY_PERIOD,
  PROFIT_LOSS_PERIOD,
  THOUSAND_SEPARATOR,
  TIMEFRAME_SETTING,
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_YEAR,
  REFRESH_PERIOD,
  EXPLORERS,
  ITEMS_PER_PAGE,
  VALUE_ROUNDING_MODE,
  AMOUNT_ROUNDING_MODE,
  DARK_MODE_ENABLED,
  LIGHT_THEME,
  DARK_THEME,
  GRAPH_ZERO_BASED
} from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';
import store from '@/store/store';
import { CURRENCY_BEFORE } from '@/typing/types';

describe('settings:mutations', () => {
  test('restore', async () => {
    const state: SettingsState = {
      [DEFI_SETUP_DONE]: true,
      [TIMEFRAME_SETTING]: TIMEFRAME_YEAR,
      [LAST_KNOWN_TIMEFRAME]: TIMEFRAME_TWO_WEEKS,
      [QUERY_PERIOD]: 5,
      [PROFIT_LOSS_PERIOD]: {
        year: '2018',
        quarter: Q3
      },
      [CURRENCY_LOCATION]: CURRENCY_BEFORE,
      [THOUSAND_SEPARATOR]: '|',
      [DECIMAL_SEPARATOR]: '-',
      [REFRESH_PERIOD]: 120,
      [EXPLORERS]: {
        ETH: {
          transaction: 'explore/tx'
        }
      },
      [ITEMS_PER_PAGE]: 25,
      [VALUE_ROUNDING_MODE]: BigNumber.ROUND_DOWN,
      [AMOUNT_ROUNDING_MODE]: BigNumber.ROUND_UP,
      [DARK_MODE_ENABLED]: true,
      [LIGHT_THEME]: {
        primary: '#000000',
        accent: '#ffffff',
        graph: '#555555'
      },
      [DARK_THEME]: {
        primary: '#ffffff',
        accent: '#000000',
        graph: '#555555'
      },
      [GRAPH_ZERO_BASED]: true
    };
    store.commit('settings/restore', state);
    const settings = store.state.settings!;
    expect(settings[DEFI_SETUP_DONE]).toBe(true);
    expect(settings[TIMEFRAME_SETTING]).toBe(TIMEFRAME_YEAR);
    expect(settings[LAST_KNOWN_TIMEFRAME]).toBe(TIMEFRAME_TWO_WEEKS);
    expect(settings[QUERY_PERIOD]).toBe(5);
    expect(settings[PROFIT_LOSS_PERIOD]).toMatchObject({
      year: '2018',
      quarter: Q3
    });
    expect(settings[THOUSAND_SEPARATOR]).toBe('|');
    expect(settings[DECIMAL_SEPARATOR]).toBe('-');
    expect(settings[CURRENCY_LOCATION]).toBe(CURRENCY_BEFORE);
    expect(settings[REFRESH_PERIOD]).toBe(120);
    expect(settings[EXPLORERS]).toStrictEqual({
      ETH: {
        transaction: 'explore/tx'
      }
    });
    expect(settings[ITEMS_PER_PAGE]).toBe(25);
    expect(settings[VALUE_ROUNDING_MODE]).toBe(BigNumber.ROUND_DOWN);
    expect(settings[AMOUNT_ROUNDING_MODE]).toBe(BigNumber.ROUND_UP);
    expect(settings[DARK_MODE_ENABLED]).toBe(true);
    expect(settings[LIGHT_THEME]).toStrictEqual({
      primary: '#000000',
      accent: '#ffffff',
      graph: '#555555'
    });
    expect(settings[DARK_THEME]).toStrictEqual({
      primary: '#ffffff',
      accent: '#000000',
      graph: '#555555'
    });
    expect(settings[GRAPH_ZERO_BASED]).toBe(true);
  });
});
