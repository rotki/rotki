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
  TIMEFRAME_YEAR
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
      [DECIMAL_SEPARATOR]: '-'
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
  });
});
