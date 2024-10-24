import { type AssetBalanceWithPrice, AssetBalances } from '@/types/balances';
import { Section, Status } from '@/types/status';
import { TaskType } from '@/types/task-type';
import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type {
  ExchangeData,
  ExchangeInfo,
  ExchangeSavingsCollection,
  ExchangeSavingsCollectionResponse,
  ExchangeSavingsRequestPayload,
} from '@/types/exchanges';
import type { AssetPrices } from '@/types/prices';
import type { ExchangeMeta, TaskMeta } from '@/types/task';
import type { AssetBreakdown, ExchangeBalancePayload } from '@/types/blockchain/accounts';

export const useExchangeBalancesStore = defineStore('balances/exchanges', () => {
  const exchangeBalances = ref<ExchangeData>({});

  const { t } = useI18n();

  const { awaitTask, isTaskRunning, metadata } = useTaskStore();
  const { notify } = useNotificationsStore();
  const { getAssociatedAssetIdentifier } = useAssetInfoRetrieval();
  const { isAssetIgnored } = useIgnoredAssetsStore();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { assetPrice } = useBalancePricesStore();
  const { queryExchangeBalances, getExchangeSavings, getExchangeSavingsTask } = useExchangeApi();
  const { toSortedAssetBalanceWithPrice } = useBalanceSorting();

  const exchanges = computed<ExchangeInfo[]>(() => {
    const balances = get(exchangeBalances);
    return Object.keys(balances)
      .map(value => ({
        location: value,
        balances: balances[value],
        total: assetSum(balances[value]),
      }))
      .sort((a, b) => sortDesc(a.total, b.total));
  });

  const balances = computed<AssetBalances>(() =>
    sumAssetBalances(Object.values(get(exchangeBalances)), getAssociatedAssetIdentifier),
  );

  const getBreakdown = (asset: string): ComputedRef<AssetBreakdown[]> => computed<AssetBreakdown[]>(() => {
    const breakdown: AssetBreakdown[] = [];
    const cexBalances = get(exchangeBalances);
    for (const exchange in cexBalances) {
      const exchangeData = cexBalances[exchange];
      for (const exchangeDataAsset in exchangeData) {
        const associatedAsset = get(getAssociatedAssetIdentifier(exchangeDataAsset));
        if (associatedAsset !== asset)
          continue;

        breakdown.push({
          address: '',
          location: exchange,
          tags: [],
          ...exchangeData[exchangeDataAsset],
        });
      }
    }
    return breakdown;
  });

  const getBalances = (
    exchange: string,
    hideIgnored = true,
  ): ComputedRef<AssetBalanceWithPrice[]> => computed<AssetBalanceWithPrice[]>(() => {
    const balances = get(exchangeBalances);

    if (balances && balances[exchange]) {
      return toSortedAssetBalanceWithPrice(
        get(mergeAssociatedAssets(balances[exchange], getAssociatedAssetIdentifier)),
        asset => hideIgnored && get(isAssetIgnored(asset)),
        assetPrice,
      );
    }

    return [];
  });

  const getLocationBreakdown = (id: string): ComputedRef<Record<string, AssetBalanceWithPrice>> => computed(() => {
    const assets: Record<string, AssetBalanceWithPrice> = {};
    const exchange = get(connectedExchanges).find(({ location }) => id === location);

    if (exchange) {
      const balances = get(getBalances(exchange.location));
      for (const balance of balances)
        appendAssetBalance(balance, assets, getAssociatedAssetIdentifier);
    }
    return assets;
  });

  const getByLocationBalances = (
    convert: (bn: MaybeRef<BigNumber>) => MaybeRef<BigNumber>,
  ): ComputedRef<Record<string, BigNumber>> => computed<Record<string, BigNumber>>(() => {
    const balances: Record<string, BigNumber> = {};
    for (const { location, total } of get(exchanges)) {
      const balance = balances[location];
      const value = get(convert(total));
      balances[location] = !balance ? value : value.plus(balance);
    }
    return balances;
  });

  const fetchExchangeBalances = async (payload: ExchangeBalancePayload): Promise<void> => {
    const { location, ignoreCache } = payload;
    const taskType = TaskType.QUERY_EXCHANGE_BALANCES;
    const meta = metadata<ExchangeMeta>(taskType);

    if (get(isTaskRunning(taskType)) && meta?.location === location)
      return;

    const { setStatus, resetStatus, isFirstLoad } = useStatusUpdater(Section.EXCHANGES);

    const newStatus = isFirstLoad() ? Status.LOADING : Status.REFRESHING;
    setStatus(newStatus);

    try {
      const { taskId } = await queryExchangeBalances(location, ignoreCache);
      const meta: ExchangeMeta = {
        location,
        title: t('actions.balances.exchange_balances.task.title', {
          location,
        }),
      };

      const { result } = await awaitTask<AssetBalances, ExchangeMeta>(taskId, taskType, meta, true);

      set(exchangeBalances, {
        ...get(exchangeBalances),
        [location]: AssetBalances.parse(result),
      });
      setStatus(Status.LOADED);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const message = t('actions.balances.exchange_balances.error.message', {
          location,
          error: error.message,
        });
        const title = t('actions.balances.exchange_balances.error.title', {
          location,
        });

        notify({
          title,
          message,
          display: true,
        });
      }
      resetStatus();
    }
  };

  const fetchConnectedExchangeBalances = async (refresh = false): Promise<void> => {
    const exchanges = get(connectedExchanges);
    for (const exchange of exchanges) {
      await fetchExchangeBalances({
        location: exchange.location,
        ignoreCache: refresh,
      });
    }
  };

  const updatePrices = (prices: MaybeRef<AssetPrices>): void => {
    const exchanges = { ...get(exchangeBalances) };
    for (const exchange in exchanges) exchanges[exchange] = updateBalancesPrices(exchanges[exchange], prices);

    set(exchangeBalances, exchanges);
  };

  const fetchExchangeSavings = async (
    payload: MaybeRef<ExchangeSavingsRequestPayload>,
  ): Promise<ExchangeSavingsCollection> => {
    const response = await getExchangeSavings({
      ...get(payload),
      onlyCache: true,
    });

    return mapCollectionResponse(response);
  };

  const syncExchangeSavings = async (location: string): Promise<boolean> => {
    const taskType = TaskType.QUERY_EXCHANGE_SAVINGS;

    const defaults: ExchangeSavingsRequestPayload = {
      limit: 0,
      offset: 0,
      ascending: [false],
      orderByAttributes: ['timestamp'],
      onlyCache: false,
      location,
    };

    const { taskId } = await getExchangeSavingsTask(defaults);

    const taskMeta = {
      title: t('actions.balances.exchange_savings_interest.task.title', {
        location,
      }),
    };

    try {
      await awaitTask<ExchangeSavingsCollectionResponse, TaskMeta>(taskId, taskType, taskMeta, true);
      return true;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.balances.exchange_savings_interest.error.title', {
            location,
          }),
          message: t('actions.balances.exchange_savings_interest.error.message', { location }),
          display: true,
        });
      }
    }

    return false;
  };

  const refreshExchangeSavings = async (userInitiated = false): Promise<void> => {
    const { setStatus, resetStatus, fetchDisabled } = useStatusUpdater(Section.EXCHANGE_SAVINGS);

    if (fetchDisabled(userInitiated)) {
      logger.info('skipping exchanges savings');
      return;
    }

    setStatus(Status.REFRESHING);

    try {
      const locations = get(connectedExchanges)
        .map(({ location }) => location)
        .filter(uniqueStrings)
        .filter(location => ['binance', 'binanceus'].includes(location));

      if (locations.length > 0)
        await Promise.all(locations.map(syncExchangeSavings));

      setStatus(get(isTaskRunning(TaskType.QUERY_EXCHANGE_SAVINGS)) ? Status.REFRESHING : Status.LOADED);
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
  };

  return {
    exchanges,
    exchangeBalances,
    balances,
    getBalances,
    fetchExchangeBalances,
    fetchConnectedExchangeBalances,
    getBreakdown,
    getLocationBreakdown,
    getByLocationBalances,
    updatePrices,
    fetchExchangeSavings,
    refreshExchangeSavings,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useExchangeBalancesStore, import.meta.hot));
