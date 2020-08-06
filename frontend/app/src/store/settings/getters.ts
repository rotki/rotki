import { GetterTree } from 'vuex';
import { SettingsState } from '@/store/settings/types';
import { RotkehlchenState } from '@/store/store';

export type SettingsGetters = {};

type GettersDefinition<S = SettingsState, G = SettingsGetters> = {
  [P in keyof G]: (state: S, getters: G) => G[P];
};

export const getters: GetterTree<SettingsState, RotkehlchenState> &
  GettersDefinition = {};
