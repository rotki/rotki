import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { MutationTree } from 'vuex';
import {
  QueriedAddresses,
  Watcher,
  WatcherTypes
} from '@/services/session/types';
import { defaultState } from '@/store/session/state';
import { SessionState, SyncConflict } from '@/store/session/types';
import {
  AccountingSettings,
  AccountingSettingsUpdate,
  GeneralSettings,
  Tags
} from '@/types/user';

export const mutations: MutationTree<SessionState> = {
  login(
    state: SessionState,
    payload: { username: string; newAccount: boolean }
  ) {
    const { username, newAccount } = payload;
    state.logged = true;
    state.newAccount = newAccount;
    state.username = username;
  },
  completeLogin(state: SessionState, complete: boolean) {
    state.loginComplete = complete;
  },
  generalSettings(state: SessionState, settings: GeneralSettings) {
    state.generalSettings = Object.assign(state.generalSettings, settings);
  },
  privacyMode(state: SessionState, privacyMode: number) {
    state.privacyMode = privacyMode;
  },
  scrambleData(state: SessionState, scrambleData: boolean) {
    state.scrambleData = scrambleData;
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
  reset(state: SessionState) {
    Object.assign(state, defaultState());
  },
  syncConflict(state: SessionState, syncConflict: SyncConflict) {
    state.syncConflict = syncConflict;
  },
  tags(state: SessionState, tags: Tags) {
    state.tags = { ...tags };
  },
  watchers(state: SessionState, watchers: Watcher<WatcherTypes>[]) {
    state.watchers = watchers;
  },
  queriedAddresses(state: SessionState, queriedAddresses: QueriedAddresses) {
    state.queriedAddresses = queriedAddresses;
  },
  ignoreAssets(state: SessionState, ignoredAssets: string[]) {
    state.ignoredAssets = ignoredAssets;
  },
  updateLastBalanceSave(state: SessionState, lastBalanceSave: number) {
    state.lastBalanceSave = lastBalanceSave;
  },
  updateLastDataUpload(state: SessionState, lastDataUpload: number) {
    state.lastDataUpload = lastDataUpload;
  },
  setTimeframe(state: SessionState, timeframe: TimeFramePeriod) {
    state.timeframe = timeframe;
  },
  setShowUpdatePopup(state: SessionState, showUpdatePopup: boolean) {
    state.showUpdatePopup = showUpdatePopup;
  }
};
