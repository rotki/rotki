import { GetterTree } from 'vuex';
import { RotkehlchenState } from '@/store/store';
import { SessionState } from '@/store/session/state';

export const getters: GetterTree<SessionState, RotkehlchenState> = {
  floatingPrecision: (state: SessionState) => {
    return state.settings.floatingPrecision;
  },

  dateDisplayFormat: (state: SessionState) => {
    return state.settings.dateDisplayFormat;
  },

  lastBalanceSave: (state: SessionState) => {
    return state.accountingSettings.lastBalanceSave;
  },

  currency: (state: SessionState) => {
    return state.settings.selectedCurrency;
  },

  tags: (state: SessionState) => {
    return Object.values(state.tags);
  }
};
