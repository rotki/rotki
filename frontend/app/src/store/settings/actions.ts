import { ActionContext, ActionTree } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { FrontendSettingsPayload, SettingsState } from '@/store/settings/types';
import { RotkehlchenState } from '@/store/types';

interface Actions {
  updateSetting(
    context: ActionContext<SettingsState, RotkehlchenState>,
    payload: FrontendSettingsPayload
  ): Promise<void>;
}

export const actions: ActionTree<SettingsState, RotkehlchenState> & Actions = {
  async updateSetting({ commit, state }, payload: FrontendSettingsPayload) {
    const props = Object.entries(payload);
    if (props.length === 0) {
      return;
    }

    for (const [prop, value] of props) {
      commit(prop, value);
    }

    try {
      await api.setSettings({
        frontend_settings: JSON.stringify(state)
      });
      // eslint-disable-next-line no-empty
    } catch (e) {}
  }
};
