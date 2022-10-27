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
import { uniqueStrings } from '@/utils/data';

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
  const { getAssetPrice, fetchPrices, fetchExchangeRates } = priceStore;
  const { notify } = useNotifications();
  const { isTaskRunning, addTask } = useTasks();
  const { tc } = useI18n();

  const adjustPrices = (prices: MaybeRef<AssetPrices>) => {
    updateChainPrices(prices);
    updateManualPrices(prices);
    updateExchangePrices(prices);
  };

  const refreshPrices = async (
    ignoreCache: boolean = false,
    selectedAssets: string[] | null = null
  ): Promise<void> => {
    const unique = selectedAssets ? selectedAssets.filter(uniqueStrings) : null;
    const { setStatus } = useStatusUpdater(Section.PRICES);
    setStatus(Status.LOADING);
    if (ignoreCache) {
      await fetchExchangeRates();
    }
    await fetchPrices({
      ignoreCache,
      selectedAssets: get(unique && unique.length > 0 ? unique : assets())
    });
    adjustPrices(get(prices));
    setStatus(Status.LOADED);
  };

  watchThrottled(
    assets(),
    async assets => {
      const noPriceAssets = assets.filter(asset => !getAssetPrice(asset));
      if (noPriceAssets.length > 0) {
        await refreshPrices(false, noPriceAssets);
      }
    },
    { throttle: 800 }
  );

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
    await fetchExchangeRates();
    await fetchBalances();
    await Promise.allSettled([
      fetchManualBalances(),
      refreshAccounts(),
      fetchConnectedExchangeBalances(),
      fetchNonFungibleBalances()
    ]);
  };

  const autoRefresh = async () => {
    await Promise.allSettled([
      fetchManualBalances(),
      refreshAccounts(),
      fetchConnectedExchangeBalances()
    ]);

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
