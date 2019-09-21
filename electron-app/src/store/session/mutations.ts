import { MutationTree } from 'vuex';
import { defaultState, SessionState } from '@/store/session/state';
import { Currency } from '@/model/currency';
import {
  AccountingSettings,
  AccountingSettingsUpdate,
  GeneralSettings
} from '@/typing/types';

export const mutations: MutationTree<SessionState> = {
  defaultCurrency(state: SessionState, currency: Currency) {
    state.currency = currency;
  },
  logged(state: SessionState, logged: boolean) {
    state.logged = logged;
  },
  settings(state: SessionState, settings: GeneralSettings) {
    state.settings = { ...settings };
  },
  premium(state: SessionState, premium: boolean) {
    state.premium = premium;
  },
  premiumSync(state: SessionState, premiumSync: boolean) {
    state.premiumSync = premiumSync;
  },
  accountingSettings(
    state: SessionState,
    accountingSettings: AccountingSettings
  ) {
    state.accountingSettings = { ...accountingSettings };
  },
  updateAccountingSetting(
    state: SessionState,
    setting: AccountingSettingsUpdate
  ) {
    state.accountingSettings = { ...state.accountingSettings, ...setting };
  },
  newUser(state: SessionState, newUser: boolean) {
    state.newUser = newUser;
  },
  nodeConnection(state: SessionState, nodeConnection: boolean) {
    state.nodeConnection = nodeConnection;
  },
  reset(state: SessionState) {
    state = Object.assign(state, defaultState());
  }
};
