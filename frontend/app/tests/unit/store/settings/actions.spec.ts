import { api } from '@/services/rotkehlchen-api';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';
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
        frontend_settings: JSON.stringify({ [DEFI_SETUP_DONE]: true })
      })
    );
  });

  test('does not update settings on missing payload', async () => {
    expect.assertions(1);
    await store.dispatch(
      'settings/updateSetting',
      {} as FrontendSettingsPayload
    );

    expect(api.setSettings).toHaveBeenCalledTimes(0);
  });
});
