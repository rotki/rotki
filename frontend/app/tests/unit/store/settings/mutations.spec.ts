import { TIMEFRAME_YEAR } from '@/components/dashboard/const';
import { DASHBOARD_TIMEFRAME, DEFI_SETUP_DONE } from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';
import store from '@/store/store';

describe('settings:mutations', () => {
  test('restore', async () => {
    const state: SettingsState = {
      [DEFI_SETUP_DONE]: true,
      [DASHBOARD_TIMEFRAME]: TIMEFRAME_YEAR
    };
    store.commit('settings/restore', state);
    expect(store.state.settings!.defiSetupDone).toBe(true);
    expect(store.state.settings!.dashboardTimeframe).toBe(TIMEFRAME_YEAR);
  });
});
