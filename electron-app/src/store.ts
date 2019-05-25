import Vue from 'vue';
import Vuex, { StoreOptions } from 'vuex';
import { Currency } from '@/model/currency';
import { currencies } from '@/data/currencies';
import {
  AccountingSettings,
  AccountingSettingsUpdate,
  GeneralSettings
} from '@/typing/types';
import { defaultAccountingSettings, defaultSettings } from '@/data/factories';

Vue.use(Vuex);

let store: StoreOptions<RotkehlchenState> = {
  state: {
    currency: currencies[0],
    userLogged: false,
    settings: defaultSettings(),
    accountingSettings: defaultAccountingSettings(),
    logout: false,
    premium: false,
    premiumSync: false
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
    },
    premium(state: RotkehlchenState, premium: boolean) {
      state.premium = premium;
    },
    premiumSync(state: RotkehlchenState, premiumSync: boolean) {
      state.premiumSync = premiumSync;
    },
    accountingSettings(
      state: RotkehlchenState,
      accountingSettings: AccountingSettings
    ) {
      state.accountingSettings = Object.assign({}, accountingSettings);
    },
    updateAccountingSetting(
      state: RotkehlchenState,
      setting: AccountingSettingsUpdate
    ) {
      state.accountingSettings = Object.assign(
        {},
        state.accountingSettings,
        setting
      );
    }
  },
  actions: {}
};
export default new Vuex.Store(store);

export interface RotkehlchenState {
  currency: Currency;
  userLogged: boolean;
  settings: GeneralSettings;
  accountingSettings: AccountingSettings;
  logout: boolean;
  premium: boolean;
  premiumSync: boolean;
}
