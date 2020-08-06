import { MutationTree } from 'vuex';
import { DEFI_SETUP_DONE } from '@/store/settings/consts';
import { defaultState } from '@/store/settings/state';
import { SettingsState } from '@/store/settings/types';
import { Writeable } from '@/types';

export type Mutations<S = SettingsState> = {
  [DEFI_SETUP_DONE](state: S, done: boolean): void;
  restore(state: S, persisted: S): void;
  reset(state: S): void;
};

export const mutations: MutationTree<SettingsState> & Mutations = {
  [DEFI_SETUP_DONE](state: Writeable<SettingsState>, done: boolean) {
    state.defiSetupDone = done;
  },
  restore(state: SettingsState, persisted: SettingsState) {
    Object.assign(state, persisted);
  },
  reset: (state: SettingsState) => {
    Object.assign(state, defaultState());
  }
};
