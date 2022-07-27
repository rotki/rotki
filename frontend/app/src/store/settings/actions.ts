import { BigNumber } from '@rotki/common';
import { ActionContext, ActionTree } from 'vuex';
import { getBnFormat } from '@/data/amount_formatter';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { SettingsState } from '@/store/settings/state';
import { ActionStatus, RotkehlchenState } from '@/store/types';
import {
  DECIMAL_SEPARATOR,
  FrontendSettingsPayload,
  THOUSAND_SEPARATOR
} from '@/types/frontend-settings';
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

    for (const [prop, value] of props) {
      commit(prop, value);
    }

    try {
      const settings = await api.setSettings({
        frontendSettings: JSON.stringify(axiosSnakeCaseTransformer(state))
      });

      if (payload[THOUSAND_SEPARATOR] || payload[DECIMAL_SEPARATOR]) {
        BigNumber.config({
          FORMAT: getBnFormat(
            settings.other.frontendSettings.thousandSeparator,
            settings.other.frontendSettings.decimalSeparator
          )
        });
      }

      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  }
};
