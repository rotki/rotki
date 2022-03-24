import { computed, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import isEqual from 'lodash/isEqual';
import { acceptHMRUpdate, defineStore } from 'pinia';
import { Module } from 'vuex';
import i18n from '@/i18n';
import { api } from '@/services/rotkehlchen-api';
import { BalanceState, EnsNames } from '@/store/balances/types';
import { useTasks } from '@/store/tasks';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const useEnsNamesStore = defineStore('ensNames', () => {
  const store = useStore();
  const ensAddresses = ref<string[]>([]);
  const ensNames = ref<EnsNames>({});

  const { awaitTask } = useTasks();

  const updateEnsAddresses = (newAddresses: string[]): boolean => {
    const newEnsAddresses = [...get(ensAddresses), ...newAddresses].filter(
      uniqueStrings
    );
    const currentEnsAddresses = [...get(ensAddresses)];

    const changed = !isEqual(newEnsAddresses, currentEnsAddresses);

    if (changed) {
      set(ensAddresses, newEnsAddresses);
    }

    return changed;
  };

  const updateEnsNames = (newEnsNames: EnsNames) => {
    set(ensNames, { ...get(ensNames), ...newEnsNames });
  };

  const fetchEnsNames = async (
    addresses: string[],
    forceUpdate: boolean = false
  ) => {
    if (addresses.length < 1) return;

    const changed = updateEnsAddresses(addresses);

    // Don't fetch if not forceUpdate, and no new ens names that need to be fetched.
    if (!forceUpdate && !changed) return;

    const latestEnsAddresses = get(ensAddresses);
    if (latestEnsAddresses.length > 0) {
      if (forceUpdate) {
        const taskType = TaskType.FETCH_ENS_NAMES;
        const { taskId } = await api.balances.getEnsNamesTask(
          latestEnsAddresses
        );
        const { result } = await awaitTask<EnsNames, TaskMeta>(
          taskId,
          taskType,
          {
            title: i18n.t('ens_names.task.title').toString(),
            numericKeys: []
          }
        );

        updateEnsNames(result);
      } else {
        const result = await api.balances.getEnsNames(latestEnsAddresses);
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

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useEnsNamesStore, import.meta.hot));
}
