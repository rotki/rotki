import { DEFI_SETUP_DONE } from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';
import store from '@/store/store';

describe('settings:mutations', () => {
  test('restore', async () => {
    const state: SettingsState = {
      [DEFI_SETUP_DONE]: true
    };
    store.commit('settings/restore', state);
    expect(store.state.settings!.defiSetupDone).toBe(true);
  });
});
