import { MaybeRef } from '@vueuse/core';
import { useStatusUpdater } from '@/composables/status';
import { useBalancesApi } from '@/services/balances';
import { useAggregatedBalancesStore } from '@/store/balances/aggregated';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useNonFungibleBalancesStore } from '@/store/balances/non-fungible';
import { useBalancePricesStore } from '@/store/balances/prices';
import { AllBalancePayload } from '@/store/balances/types';
import { useBlockchainStore } from '@/store/blockchain';
import { useBlockchainBalancesStore } from '@/store/blockchain/balances';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { AssetPrices } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';

export const useBalancesStore = defineStore('balances', () => {
  const { updatePrices: updateManualPrices, fetchManualBalances } =
    useManualBalancesStore();
  const { updatePrices: updateChainPrices } = useBlockchainBalancesStore();
  const { updatePrices: updateExchangePrices, fetchConnectedExchangeBalances } =
    useExchangeBalancesStore();
  const { refreshAccounts } = useBlockchainStore();
  const { fetchNonFungibleBalances } = useNonFungibleBalancesStore();
  const { assets } = useAggregatedBalancesStore();
  const { queryBalancesAsync } = useBalancesApi();
  const priceStore = useBalancePricesStore();
  const { prices } = storeToRefs(priceStore);
  const { notify } = useNotifications();
  const { isTaskRunning, addTask } = useTasks();
  const { tc } = useI18n();

  const adjustPrices = (prices: MaybeRef<AssetPrices>) => {
    updateChainPrices(prices);
    updateManualPrices(prices);
    updateExchangePrices(prices);
  };

  const refreshPrices = async (ignoreCache: boolean = false): Promise<void> => {
    const { setStatus } = useStatusUpdater(Section.PRICES);
    setStatus(Status.LOADING);
    await priceStore.fetchExchangeRates();
    await priceStore.fetchPrices({
      ignoreCache,
      selectedAssets: get(assets())
    });
    adjustPrices(get(prices));
    setStatus(Status.LOADED);
  };

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}) => {
    if (get(isTaskRunning(TaskType.QUERY_BALANCES))) {
      return;
    }
    try {
      const { taskId } = await queryBalancesAsync(payload);
      await addTask(taskId, TaskType.QUERY_BALANCES, {
        title: tc('actions.balances.all_balances.task.title'),
        ignoreResult: true
      });
    } catch (e: any) {
      notify({
        title: tc('actions.balances.all_balances.error.title'),
        message: tc('actions.balances.all_balances.error.message', 0, {
          message: e.message
        }),
        display: true
      });
    }
  };

  const fetch = async (): Promise<void> => {
    await fetchManualBalances();
    await priceStore.fetchExchangeRates();
    await fetchBalances();
    await refreshAccounts();
    await fetchConnectedExchangeBalances();
    await fetchNonFungibleBalances();
  };

  const autoRefresh = async () => {
    await fetchManualBalances();
    await refreshAccounts();
    await fetchConnectedExchangeBalances();
    await refreshPrices(true);
  };

  return {
    autoRefresh,
    refreshPrices,
    fetchBalances,
    fetch
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useBalancesStore, import.meta.hot));
}
