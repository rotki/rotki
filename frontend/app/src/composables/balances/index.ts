import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { AssetPrices } from '@/types/prices';
import type { MaybeRef } from '@vueuse/core';
import type { AllBalancePayload } from '@/types/blockchain/accounts';

export const useBalances = createSharedComposable(() => {
  const { updatePrices: updateManualPrices, fetchManualBalances } = useManualBalancesStore();
  const { updatePrices: updateChainPrices } = useBlockchainStore();
  const { updatePrices: updateExchangePrices, fetchConnectedExchangeBalances } = useExchangeBalancesStore();
  const { refreshAccounts } = useBlockchains();
  const { assets } = useAggregatedBalances();
  const { queryBalancesAsync } = useBalancesApi();
  const priceStore = useBalancePricesStore();
  const { prices } = storeToRefs(priceStore);
  const { assetPrice, fetchPrices, fetchExchangeRates } = priceStore;
  const { notify } = useNotificationsStore();
  const { isTaskRunning, awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { currency } = storeToRefs(useGeneralSettingsStore());
  const { fetchNetValue } = useStatisticsStore();
  const { logged } = storeToRefs(useSessionAuthStore());

  const adjustPrices = (prices: MaybeRef<AssetPrices>): void => {
    const updatedPrices = { ...get(prices) };
    updateChainPrices(updatedPrices);
    updateManualPrices(updatedPrices);
    updateExchangePrices(updatedPrices);
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
          title: t('actions.balances.all_balances.error.title'),
          message: t('actions.balances.all_balances.error.message', {
            message: error.message,
          }),
          display: true,
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

  // TODO: This is temporary fix for double conversion issue. Future solutions should try to eliminate this part.
  watch(currency, async () => {
    if (!get(logged))
      return;

    await refreshPrices(true);
  });

  return {
    autoRefresh,
    refreshPrices,
    fetchBalances,
    adjustPrices,
    fetch,
  };
});
