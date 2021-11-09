import { ActionContext, ActionTree } from 'vuex';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { FrontendSettingsPayload, SettingsState } from '@/store/settings/types';
import { ActionStatus, RotkehlchenState } from '@/store/types';
import { assert } from '@/utils/assertions';

interface Actions {
  updateSetting(
    context: ActionContext<SettingsState, RotkehlchenState>,
    payload: FrontendSettingsPayload
  ): Promise<ActionStatus>;
}

export const actions: ActionTree<SettingsState, RotkehlchenState> & Actions = {
  async updateSetting(
    { commit, state },
    payload: FrontendSettingsPayload
  ): Promise<ActionStatus> {
    const props = Object.entries(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    let success = false;
    let message: string | undefined;

    for (const [prop, value] of props) {
      commit(prop, value);
    }

    try {
      await api.setSettings({
        frontend_settings: JSON.stringify(axiosSnakeCaseTransformer(state))
      });
      success = true;
    } catch (e: any) {
      message = e.message;
    }
    return {
      success,
      message
    };
  }
};
