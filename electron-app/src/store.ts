import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import { GeneralSettings } from '@/typing/types';
import { defaultSettings } from '@/data/factories';

Vue.use(Vuex);

let store: StoreOptions<RotkehlchenState> = {
  state: {
    currency: currencies[0],
    userLogged: false,
    settings: defaultSettings(),
    logout: false
  },
  mutations: {
    defaultCurrency(state: RotkehlchenState, currency: Currency) {
      state.currency = currency;
    },
    logged(state: RotkehlchenState, logged: boolean) {
      state.userLogged = logged;
    },
    logout(state: RotkehlchenState, logout: boolean) {
      state.logout = logout;
    },
    settings(state: RotkehlchenState, settings: GeneralSettings) {
      state.settings = Object.assign({}, settings);
    }
  },
  actions: {}
};
export default new Vuex.Store(store);

export interface RotkehlchenState {
  currency: Currency;
  userLogged: boolean;
  settings: GeneralSettings;
  logout: boolean;
}
