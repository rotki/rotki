import { Blockchain } from '@rotki/common/lib/blockchain';
import { computed, ref, watch } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import isEqual from 'lodash/isEqual';
import { acceptHMRUpdate, defineStore, storeToRefs } from 'pinia';
import { Module } from 'vuex';
import { setupGeneralBalances } from '@/composables/balances';
import i18n from '@/i18n';
import {
  EthDetectedTokensInfo,
  EthDetectedTokensRecord
} from '@/services/balances/types';
import { api } from '@/services/rotkehlchen-api';
import {
  BalanceState,
  EthNames,
  EthNamesEntries,
  EthAddressBookLocation
} from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings';
import { useTasks } from '@/store/tasks';
import { RotkehlchenState } from '@/store/types';
import { useStore } from '@/store/utils';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';
import { isValidEthAddress } from '@/utils/text';
import { actions } from './actions';
import { getters } from './getters';
import { mutations } from './mutations';
import { state } from './state';

const namespaced: boolean = true;

export const useEthNamesStore = defineStore('ethNames', () => {
  const { enableEthNames } = storeToRefs(useFrontendSettingsStore());
  const ensAddresses = ref<string[]>([]);
  const ethNames = ref<EthNames>({});

  const ethAddressBookGlobal = ref<EthNamesEntries>([]);
  const ethAddressBookPrivate = ref<EthNamesEntries>([]);

  const ethAddressBook = computed(() => {
    return {
      global: get(ethAddressBookGlobal),
      private: get(ethAddressBookPrivate)
    };
  });

  const { awaitTask } = useTasks();
  const { notify } = useNotifications();

  const updateEnsAddresses = (newAddresses: string[]): boolean => {
    const newEnsAddresses = [...get(ensAddresses), ...newAddresses]
      .filter(uniqueStrings)
      .filter(address => isValidEthAddress(address));

    const currentEnsAddresses = [...get(ensAddresses)];

    const changed = !isEqual(newEnsAddresses, currentEnsAddresses);

    if (changed) {
      set(ensAddresses, newEnsAddresses);
    }

    return changed;
  };

  const fetchEnsNames = async (
    addresses: string[],
    forceUpdate: boolean = false
  ) => {
    if (addresses.length < 1) return;

    const changed = updateEnsAddresses(addresses);

    // Don't fetch if not forceUpdate and no new ens names that need to be fetched.
    if (!forceUpdate && !changed) return;

    const latestEnsAddresses = get(ensAddresses);
    if (latestEnsAddresses.length > 0) {
      if (forceUpdate) {
        const taskType = TaskType.FETCH_ENS_NAMES;
        const { taskId } = await api.balances.getEnsNamesTask(
          latestEnsAddresses
        );
        await awaitTask<EthNames, TaskMeta>(taskId, taskType, {
          title: i18n.t('ens_names.task.title').toString(),
          numericKeys: []
        });
      } else {
        await api.balances.getEnsNames(latestEnsAddresses);
      }
      await fetchEthNames();
    }
  };

  const fetchEthNames = async () => {
    const addresses = [
      ...get(ethAddressBookGlobal).map(item => item.address),
      ...get(ethAddressBookPrivate).map(item => item.address),
      ...get(ensAddresses)
    ].filter(uniqueStrings);

    const notifyError = (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: i18n.t('eth_names.error.title').toString(),
        message: i18n.t('eth_names.error.message', { message }).toString(),
        display: true
      });
    };

    try {
      const result = await api.balances.getEthNames(addresses);
      set(ethNames, result);
    } catch (e: any) {
      notifyError(e);
    }
  };

  const ethNameSelector = (address: string) => {
    return computed<string | null>(() => {
      if (!get(enableEthNames)) return null;
      return get(ethNames)[address] ?? null;
    });
  };

  const updateEthAddressBookState = (
    location: EthAddressBookLocation,
    result: EthNamesEntries
  ) => {
    if (location === 'global') {
      set(ethAddressBookGlobal, result);
    } else {
      set(ethAddressBookPrivate, result);
    }

    fetchEthNames();
  };

  const fetchEthAddressBook = async (
    location: EthAddressBookLocation,
    addresses?: string[]
  ) => {
    const notifyError = (error?: any) => {
      logger.error(error);
      const message = error?.message ?? error ?? '';
      notify({
        title: i18n.t('eth_address_book.actions.fetch.error.title').toString(),
        message: i18n
          .t('eth_address_book.actions.fetch.error.message', { message })
          .toString(),
        display: true
      });
    };
    try {
      const result = await api.balances.getEthAddressBook(location, addresses);
      updateEthAddressBookState(location, result);
    } catch (e: any) {
      notifyError(e);
    }
  };

  const addEthAddressBook = async (
    location: EthAddressBookLocation,
    entries: EthNamesEntries
  ) => {
    const result = await api.balances.addEthAddressBook(location, entries);

    if (result) {
      await fetchEthAddressBook(location);
    }
  };

  const updateEthAddressBook = async (
    location: EthAddressBookLocation,
    entries: EthNamesEntries
  ) => {
    const result = await api.balances.updateEthAddressBook(location, entries);

    if (result) {
      await fetchEthAddressBook(location);
    }
  };

  const deleteEthAddressBook = async (
    location: EthAddressBookLocation,
    addresses: string[]
  ) => {
    const result = await api.balances.deleteEthAddressBook(location, addresses);

    if (result) {
      await fetchEthAddressBook(location);
    }
  };

  return {
    fetchEnsNames,
    ethNames,
    ethNameSelector,
    ethAddressBook,
    ensAddresses,
    fetchEthNames,
    fetchEthAddressBook,
    addEthAddressBook,
    updateEthAddressBook,
    deleteEthAddressBook
  };
});

export const useBalancesStore = defineStore('balances', () => {
  const store = useStore();

  const ethAddresses = computed<string[]>(() => {
    return store.getters['balances/ethAddresses'];
  });

  const ethDetectedTokensRecord = ref<EthDetectedTokensRecord>({});

  const { fetchBlockchainBalances } = setupGeneralBalances();

  const fetchDetectedTokens = async (address?: string) => {
    try {
      if (address) {
        const { awaitTask } = useTasks();
        const taskType = TaskType.FETCH_DETECTED_TOKENS;

        const { taskId } = await api.balances.fetchDetectedTokensTask([
          address
        ]);

        const taskMeta = {
          title: i18n.t('actions.balances.detect_tokens.task.title').toString(),
          description: i18n
            .t('actions.balances.detect_tokens.task.description', {
              address
            })
            .toString(),
          numericKeys: [],
          address
        };

        await awaitTask<EthDetectedTokensRecord, TaskMeta>(
          taskId,
          taskType,
          taskMeta,
          true
        );

        await fetchDetectedTokens();
      } else {
        set(
          ethDetectedTokensRecord,
          await api.balances.fetchDetectedTokens(get(ethAddresses))
        );
        fetchBlockchainBalances({
          ignoreCache: true,
          blockchain: Blockchain.ETH
        });
      }
    } catch (e) {
      logger.error(e);
    }
  };

  const watchEthAddresses = () => {
    watch(ethAddresses, (curr, prev) => {
      if (!isEqual(curr, prev)) {
        fetchDetectedTokens();
      }
    });
  };

  const getEthDetectedTokensInfo = (address: string): EthDetectedTokensInfo => {
    const info = get(ethDetectedTokensRecord)?.[address] || null;
    if (!info) {
      return {
        tokens: [],
        total: 0,
        timestamp: null
      };
    }
    return {
      tokens: info.tokens || [],
      total: info.tokens ? info.tokens.length : 0,
      timestamp: info.lastUpdateTimestamp || null
    };
  };

  return {
    ethDetectedTokensRecord,
    watchEthAddresses,
    getEthDetectedTokensInfo,
    fetchDetectedTokens
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
  import.meta.hot.accept(acceptHMRUpdate(useEthNamesStore, import.meta.hot));
  import.meta.hot.accept(acceptHMRUpdate(useBalancesStore, import.meta.hot));
}
