import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  TIMEFRAME_YEAR,
  LAST_KNOWN_TIMEFRAME,
  TIMEFRAME_TWO_WEEKS,
  QUERY_PERIOD
} from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';
import store from '@/store/store';

describe('settings:mutations', () => {
  test('restore', async () => {
    const state: SettingsState = {
      [DEFI_SETUP_DONE]: true,
      [TIMEFRAME_SETTING]: TIMEFRAME_YEAR,
      [LAST_KNOWN_TIMEFRAME]: TIMEFRAME_TWO_WEEKS,
      [QUERY_PERIOD]: 5
    };
    store.commit('settings/restore', state);
    const settings = store.state.settings!;
    expect(settings[DEFI_SETUP_DONE]).toBe(true);
    expect(settings[TIMEFRAME_SETTING]).toBe(TIMEFRAME_YEAR);
    expect(settings[LAST_KNOWN_TIMEFRAME]).toBe(TIMEFRAME_TWO_WEEKS);
    expect(settings[QUERY_PERIOD]).toBe(5);
  });
});
