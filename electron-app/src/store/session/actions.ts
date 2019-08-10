import { ActionTree } from 'vuex';
import store, { RotkehlchenState } from '@/store';
import { SessionState } from '@/store/session/state';
import {
  convertToAccountingSettings,
  convertToGeneralSettings
} from '@/data/converters';
import { DBSettings } from '@/model/action-result';
import { service } from '@/services/rotkehlchen_service';
import { monitor } from '@/services/monitoring';

export const actions: ActionTree<SessionState, RotkehlchenState> = {
  start({ commit }, payload: { premium: boolean; settings: DBSettings }) {
    const { premium, settings } = payload;

    commit('premium', premium);
    commit('premiumSync', settings.premium_should_sync);
    commit('settings', convertToGeneralSettings(settings));
    commit('accountingSettings', convertToAccountingSettings(settings));
  },
  async unlock({ commit, dispatch }, payload: UnlockPayload) {
    try {
      const {
        username,
        password,
        create,
        syncApproval,
        apiKey,
        apiSecret
      } = payload;

      const response = await service.unlock_user(
        username,
        password,
        create,
        syncApproval,
        apiKey,
        apiSecret
      );

      commit('newUser', create);
      const db_settings = response.settings;
      if (!db_settings) {
        throw new Error('Unlock Failed');
      }

      await dispatch('start', {
        premium: response.premium,
        settings: db_settings
      });

      monitor.start();

      await dispatch('balances/fetch', {
        create,
        exchanges: response.exchanges
      });

      commit('logged', true);
    } catch (e) {
      console.error(e);
    }
  }
};

export interface UnlockPayload {
  readonly username: string;
  readonly password: string;
  readonly create: boolean;
  readonly syncApproval: 'yes' | 'no' | 'unknown';
  readonly apiKey: string;
  readonly apiSecret: string;
}
