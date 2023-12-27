import { type MaybeRef } from '@vueuse/core';
import { UserCancelledTaskError } from '@/types/task';
import { CURRENCY_USD } from '@/types/currencies';
import { type AssetPrices } from '@/types/prices';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import { type AllBalancePayload } from '@/types/blockchain/accounts';

export const useBalances = createSharedComposable(() => {
  const { updatePrices: updateManualPrices, fetchManualBalances } =
    useManualBalancesStore();
  const { updatePrices: updateChainPrices } = useBlockchainBalances();
  const { updatePrices: updateExchangePrices, fetchConnectedExchangeBalances } =
    useExchangeBalancesStore();
  const { refreshAccounts } = useBlockchains();
  const { assets } = useAggregatedBalances();
  const { queryBalancesAsync } = useBalancesApi();
  const priceStore = useBalancePricesStore();
  const { prices } = storeToRefs(priceStore);
  const { assetPrice, fetchPrices, fetchExchangeRates, exchangeRate } =
    priceStore;
  const { notify } = useNotificationsStore();
  const { isTaskRunning, awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { currencySymbol, currency } = storeToRefs(useGeneralSettingsStore());
  const { fetchNetValue } = useStatisticsStore();

  const adjustPrices = (prices: MaybeRef<AssetPrices>): void => {
    const pricesConvertedToUsd = { ...get(prices) };

    const mainCurrency = get(currencySymbol);
    if (mainCurrency !== CURRENCY_USD) {
      const rate = get(exchangeRate(mainCurrency)) ?? One;

      for (const asset in pricesConvertedToUsd) {
        const price = pricesConvertedToUsd[asset];

        if (price.isCurrentCurrency) {
          price.usdPrice = price.value.dividedBy(rate);
        }
      }
    }

    updateChainPrices(pricesConvertedToUsd);
    updateManualPrices(pricesConvertedToUsd);
    updateExchangePrices(pricesConvertedToUsd);
  };

  const refreshPrices = async (
    ignoreCache = false,
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

  const pendingAssets: Ref<string[]> = ref([]);
  const noPriceAssets = useArrayFilter(
    assets(),
    asset => !get(assetPrice(asset))
  );

  watchDebounced(
    noPriceAssets,
    async assets => {
      const pending = get(pendingAssets);
      const newAssets = assets.filter(asset => !pending.includes(asset));

      if (newAssets.length === 0) {
        return;
      }

      set(pendingAssets, [...pending, ...newAssets]);
      await refreshPrices(false, newAssets);
      set(
        pendingAssets,
        get(pendingAssets).filter(asset => !newAssets.includes(asset))
      );
    },
    { debounce: 800, maxWait: 2000 }
  );

  const fetchBalances = async (payload: Partial<AllBalancePayload> = {}) => {
    const taskType = TaskType.QUERY_BALANCES;
    if (get(isTaskRunning(taskType))) {
      return;
    }
    try {
      const { taskId } = await queryBalancesAsync(payload);
      await awaitTask(taskId, taskType, {
        title: t('actions.balances.all_balances.task.title')
      });
    } catch (e: any) {
      if (e instanceof UserCancelledTaskError) {
        logger.debug(e);
      } else {
        notify({
          title: t('actions.balances.all_balances.error.title'),
          message: t('actions.balances.all_balances.error.message', {
            message: e.message
          }),
          display: true
        });
      }
    }
  };

  const fetch = async (): Promise<void> => {
    await fetchExchangeRates();
    startPromise(fetchBalances());
    await Promise.allSettled([
      fetchManualBalances(),
      refreshAccounts(),
      fetchConnectedExchangeBalances()
    ]);
  };

  const autoRefresh = async () => {
    await Promise.allSettled([
      fetchManualBalances(),
      refreshAccounts(undefined, true),
      fetchConnectedExchangeBalances(),
      fetchNetValue()
    ]);

    await refreshPrices(true);
  };

  // TODO: This is temporary fix for double conversion issue. Future solutions should try to eliminate this part.
  watch(currency, async () => {
    await refreshPrices(true);
  });

  return {
    autoRefresh,
    refreshPrices,
    fetchBalances,
    adjustPrices,
    fetch
  };
});
