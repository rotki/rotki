import { startPromise } from '@shared/utils';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { uniqueStrings } from '@/utils/data';
import { isTaskCancelled } from '@/utils';
import { useStatisticsStore } from '@/store/statistics';
import { useTaskStore } from '@/store/tasks';
import { useNotificationsStore } from '@/store/notifications';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useExchangeBalancesStore } from '@/store/balances/exchanges';
import { useBlockchainStore } from '@/store/blockchain';
import { useManualBalancesStore } from '@/store/balances/manual';
import { useBalancesApi } from '@/composables/api/balances';
import { useStatusUpdater } from '@/composables/status';
import { useBlockchains } from '@/composables/blockchain';
import { useAggregatedBalances } from '@/composables/balances/aggregated';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import type { AllBalancePayload } from '@/types/blockchain/accounts';

export const useBalances = createSharedComposable(() => {
  const { fetchManualBalances, updatePrices: updateManualPrices } = useManualBalancesStore();
  const { updatePrices: updateChainPrices } = useBlockchainStore();
  const { fetchConnectedExchangeBalances, updatePrices: updateExchangePrices } = useExchangeBalancesStore();
  const { refreshAccounts } = useBlockchains();
  const { assets } = useAggregatedBalances();
  const { queryBalancesAsync } = useBalancesApi();
  const priceStore = useBalancePricesStore();
  const { prices } = storeToRefs(priceStore);
  const { assetPrice, fetchExchangeRates, fetchPrices } = priceStore;
  const { notify } = useNotificationsStore();
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { t } = useI18n();
  const { fetchNetValue } = useStatisticsStore();

  const adjustPrices = (prices: MaybeRef<AssetPrices>): void => {
    const pricesConvertedToUsd = { ...get(prices) };
    updateChainPrices(pricesConvertedToUsd);
    updateManualPrices(pricesConvertedToUsd);
    updateExchangePrices(pricesConvertedToUsd);
  };

  const refreshPrices = async (ignoreCache = false, selectedAssets: string[] | null = null): Promise<void> => {
    const unique = selectedAssets ? selectedAssets.filter(uniqueStrings) : null;
    const { setStatus } = useStatusUpdater(Section.PRICES);
    setStatus(Status.LOADING);
    if (ignoreCache)
      await fetchExchangeRates();

    await fetchPrices({
      ignoreCache,
      selectedAssets: get(unique && unique.length > 0 ? unique : assets()),
    });
    adjustPrices(get(prices));
    setStatus(Status.LOADED);
  };

  const pendingAssets = ref<string[]>([]);
  const noPriceAssets = useArrayFilter(assets(), asset => !get(assetPrice(asset)));

  watchDebounced(
    noPriceAssets,
    async (assets) => {
      const pending = get(pendingAssets);
      const newAssets = assets.filter(asset => !pending.includes(asset));

      if (newAssets.length === 0)
        return;

      set(pendingAssets, [...pending, ...newAssets]);
      await refreshPrices(false, newAssets);
      set(
        pendingAssets,
        get(pendingAssets).filter(asset => !newAssets.includes(asset)),
      );
    },
    { debounce: 800, maxWait: 2000 },
  );

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}): Promise<void> => {
    const taskType = TaskType.QUERY_BALANCES;
    if (get(isTaskRunning(taskType)))
      return;

    try {
      const { taskId } = await queryBalancesAsync(payload);
      await awaitTask(taskId, taskType, {
        title: t('actions.balances.all_balances.task.title'),
      });
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.balances.all_balances.error.message', {
            message: error.message,
          }),
          title: t('actions.balances.all_balances.error.title'),
        });
      }
    }
  };

  const fetch = async (): Promise<void> => {
    await fetchExchangeRates();
    startPromise(fetchBalances());
    await Promise.allSettled([fetchManualBalances(), refreshAccounts(), fetchConnectedExchangeBalances()]);
  };

  const autoRefresh = async (): Promise<void> => {
    await Promise.allSettled([
      fetchManualBalances(),
      refreshAccounts(undefined, true),
      fetchConnectedExchangeBalances(),
      fetchNetValue(),
    ]);

    await refreshPrices(true);
  };

  return {
    adjustPrices,
    autoRefresh,
    fetch,
    fetchBalances,
    refreshPrices,
  };
});
