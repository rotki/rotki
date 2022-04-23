import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { Module } from 'vuex';
import { api } from '@/services/rotkehlchen-api';
import { BalanceState, EnsNames } from '@/store/balances/types';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { uniqueStrings } from '@/utils/data';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const useEnsNames = defineStore('ensNames', () => {
  const store = useStore();
  const ensAddresses = ref<string[]>([]);
  const ensNames = ref<EnsNames>({});

  const updateEnsAddresses = (newAddresses: string[]) => {
    set(
      ensAddresses,
      [...get(ensAddresses), ...newAddresses].filter(uniqueStrings)
    );
  };

  const updateEnsNames = (newEnsNames: EnsNames) => {
    set(ensNames, { ...get(ensNames), ...newEnsNames });
  };

  const fetchEnsNames = async (
    addresses: string[],
    forceUpdate: boolean = false
  ) => {
    if (addresses.length > 0 || forceUpdate) {
      updateEnsAddresses(addresses);

      const latestEnsAddresses = get(ensAddresses);
      if (latestEnsAddresses.length > 0) {
        const result = await api.balances.getEnsNames(
          forceUpdate,
          latestEnsAddresses
        );

        updateEnsNames(result);
      }
    }
  };

  const isEnsEnabled = computed<boolean>(() => {
    return store.state.settings!!.enableEns;
  });

  const ensNameSelector = (address: string) => {
    return computed<string | null>(() => {
      if (!get(isEnsEnabled)) return null;
      return get(ensNames)[address] ?? null;
    });
  };

  return {
    fetchEnsNames,
    ensNames,
    ensNameSelector
  };
});

export const balances: Module<BalanceState, RotkehlchenState> = {
  namespaced,
  mutations,
  actions,
  state,
  getters
};

if (module.hot) {
  module.hot.accept(acceptHMRUpdate(useEnsNames, module.hot));
}
