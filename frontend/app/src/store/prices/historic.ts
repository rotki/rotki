import { type BigNumber } from '@rotki/common';
import { type ComputedRef } from 'vue';
import { type MaybeRef } from '@vueuse/core';
import { HistoricPrices } from '@/types/prices';
import { TaskType } from '@/types/task-type';
import { type TaskMeta } from '@/types/task';
import { NoPrice } from '@/utils/bignumbers';

const CACHE_EXPIRY = 1000 * 60 * 10;
const CACHE_SIZE = 500;

export const useHistoricCachePriceStore = defineStore(
  'prices/historic-cache',
  () => {
    const { queryHistoricalRates } = usePriceApi();

    const { awaitTask } = useTaskStore();
    const { t, tc } = useI18n();

    const recent: Map<string, number> = new Map();
    const unknown: Map<string, number> = new Map();
    const cache: Ref<Record<string, BigNumber>> = ref({});
    const pending: Ref<Record<string, boolean>> = ref({});
    const batch: Ref<string[]> = ref([]);

    const deleteCacheKey = (key: string): void => {
      const copy = { ...get(cache) };
      delete copy[key];
      set(cache, copy);
    };

    const updateCacheKey = (key: string, value: BigNumber): void => {
      set(cache, { ...get(cache), [key]: value });
    };

    const setPending = (key: string): void => {
      set(pending, { ...get(pending), [key]: true });

      const currentBatch = get(batch);
      if (!currentBatch.includes(key)) {
        set(batch, [...currentBatch, key]);
      }
    };

    const resetPending = (key: string): void => {
      const copy = { ...get(pending) };
      delete copy[key];
      set(pending, copy);
    };

    const put = (key: string, price: BigNumber): void => {
      recent.delete(key);

      if (recent.size === CACHE_SIZE) {
        logger.debug(`Hit cache size of ${CACHE_SIZE} going to evict items`);
        const removeKey = recent.keys().next().value;
        recent.delete(removeKey);
        deleteCacheKey(removeKey);
      }
      recent.set(key, Date.now() + CACHE_EXPIRY);
      updateCacheKey(key, price);
    };

    const fetchBatch = useDebounceFn(async () => {
      const currentBatch = get(batch);
      set(batch, []);
      await fetchHistoricPrices(currentBatch);
    }, 800);

    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

    const fetchHistoricPrices = async (keys: string[]) => {
      const taskType = TaskType.FETCH_HISTORIC_PRICE;

      const assetsTimestamp = keys.map(key => key.split('#'));
      const targetAsset = get(currencySymbol);

      try {
        const { taskId } = await queryHistoricalRates({
          assetsTimestamp,
          targetAsset
        });
        const { result } = await awaitTask<HistoricPrices, TaskMeta>(
          taskId,
          taskType,
          {
            title: t(
              'actions.balances.historic_fetch_price.task.title'
            ).toString(),
            description: tc(
              'actions.balances.historic_fetch_price.task.description',
              2,
              {
                count: assetsTimestamp.length,
                toAsset: targetAsset
              }
            )
          },
          true
        );

        const response = HistoricPrices.parse(result);
        for (const assetTimestamp of assetsTimestamp) {
          const [fromAsset, timestamp] = assetTimestamp;
          const key = `${fromAsset}#${timestamp}`;

          const item = response.assets?.[fromAsset]?.[timestamp];

          if (item) {
            put(key, item);
          } else {
            logger.debug(`unknown key: ${key}`);
            unknown.set(key, Date.now() + CACHE_EXPIRY);
          }
        }
      } catch (e: any) {
        logger.error(e);
      } finally {
        for (const key of keys) {
          resetPending(key);
        }
      }
    };

    const historicPriceInCurrentCurrency = (
      fromAsset: string,
      timestamp: number
    ): ComputedRef<BigNumber> =>
      computed(() => {
        const key = `${fromAsset}#${timestamp}`;

        if (get(isPending(key))) {
          return NoPrice;
        }

        return get(retrieve(key)) || NoPrice;
      });

    const batchPromise = async () => await fetchBatch();
    const queueIdentifier = (key: string): void => {
      const unknownExpiry = unknown.get(key);
      if (unknownExpiry && unknownExpiry >= Date.now()) {
        return;
      }

      if (unknown.has(key)) {
        unknown.delete(key);
      }
      setPending(key);
      startPromise(batchPromise());
    };

    const retrieve = (key: string): ComputedRef<BigNumber | null> => {
      const cached = get(cache)[key];
      const now = Date.now();
      let expired = false;
      if (recent.has(key) && cached) {
        const expiry = recent.get(key);
        recent.delete(key);

        if (expiry && expiry > now) {
          expired = true;
          recent.set(key, now + CACHE_EXPIRY);
        }
      }

      if (!get(pending)[key] && !expired) {
        queueIdentifier(key);
      }

      return computed(() => get(cache)[key] ?? null);
    };

    const isPending = (identifier: MaybeRef<string>): ComputedRef<boolean> =>
      computed(() => get(pending)[get(identifier)] ?? false);

    const reset = (): void => {
      set(pending, {});
      set(cache, {});
      set(batch, []);
      recent.clear();
      unknown.clear();
    };

    watch(currencySymbol, () => {
      reset();
    });

    return {
      cache,
      isPending,
      retrieve,
      reset,
      historicPriceInCurrentCurrency
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useHistoricCachePriceStore, import.meta.hot)
  );
}
