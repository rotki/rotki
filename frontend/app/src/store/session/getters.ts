import { GetterTree } from 'vuex';
import { SessionState } from '@/store/session/state';
import { RotkehlchenState } from '@/store/store';

export const getters: GetterTree<SessionState, RotkehlchenState> = {
  floatingPrecision: (state: SessionState) => {
    return state.generalSettings.floatingPrecision;
  },

  dateDisplayFormat: (state: SessionState) => {
    return state.generalSettings.dateDisplayFormat;
  },

  lastBalanceSave: (state: SessionState) => {
    return state.accountingSettings.lastBalanceSave;
  },

  currency: (state: SessionState) => {
    return state.generalSettings.selectedCurrency;
  },

  tags: (state: SessionState) => {
    return Object.values(state.tags);
  },

  krakenAccountType: (state: SessionState) => {
    return state.generalSettings.krakenAccountType;
  }
};
