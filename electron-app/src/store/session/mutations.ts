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
    state.settings = Object.assign(state.settings, {
      selectedCurrency: currency
    });
  },
  login(
    state: SessionState,
    payload: { username: string; newAccount: boolean }
  ) {
    const { username, newAccount } = payload;
    state.logged = true;
    state.newAccount = newAccount;
    state.username = username;
  },
  settings(state: SessionState, settings: GeneralSettings) {
    state.settings = Object.assign(state.settings, settings);
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
  nodeConnection(state: SessionState, nodeConnection: boolean) {
    state.nodeConnection = nodeConnection;
  },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  reset(state: SessionState) {
    state = Object.assign(state, defaultState());
  }
};
