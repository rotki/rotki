import type { ComputedRef, Ref } from 'vue';
import type { TaskError } from '@/modules/core/tasks/task-result';
import {
  type BigNumber,
  type CommonQueryStatusData,
  type FailedHistoricalAssetPriceResponse,
  NoPrice,
} from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getOr, map as mapResult, ok, type Result } from 'plainfp/result';
import { HistoricPrices } from '@/modules/assets/prices/price-types';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { SECONDS_PER_HOUR } from '@/modules/core/common/constraints';
import { createItemCache } from '@/modules/core/common/use-item-cache';
import { onSessionCleared } from '@/modules/core/session/session-lifecycle';
import { useSetting } from '@/modules/settings/use-setting';
import { UMBRELLA_LANE } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseHistoricPriceCacheReturn {
  cache: ReturnType<typeof createItemCache<BigNumber>>['cache'];
  createKey: (fromAsset: string, timestamp: number | string) => string;
  failedDailyPrices: Ref<Record<string, FailedHistoricalAssetPriceResponse>>;
  getHistoricPrice: (fromAsset: string, timestamp: number) => BigNumber;
  getIsPending: (identifier: string) => boolean;
  historicalDailyPriceStatus: Ref<CommonQueryStatusData | undefined>;
  historicPriceInCurrentCurrency: (fromAsset: string, timestamp: number) => ComputedRef<BigNumber>;
  isPending: ReturnType<typeof createItemCache<BigNumber>>['isPending'];
  resolvedFailedDailyPrices: Ref<Record<string, number[]>>;
  reset: () => void;
  resetHistoricalPricesData: (items: { fromAsset: string; timestamp: number }[]) => void;
  resolve: (key: string) => BigNumber | null;
  unknown: Map<string, number>;
}

/**
 * Monotonic batch counter behind the activity id of each batched historic-price fetch.
 *
 * @remarks
 * `createItemCache` debounces keys into batches and can have several in flight at once, so each
 * needs an id of its own: a shared one would let `submitTask` dedup two different key sets onto
 * one promise and resolve a batch with the other's prices.
 *
 * Module-scoped on purpose: the composable is shared and can be disposed/re-created while a batch
 * is still in flight, and a per-instance counter would restart and collide with that batch's id.
 */
let batchSequence = 0;

/**
 * The umbrella row the batches in flight share, so the dock shows one "Prices" row with the batches
 * as its children instead of one row per batch, each reporting the same progress.
 *
 * @remarks
 * Batches arrive one at a time from the debounced item cache, so unlike a known list the umbrella
 * opens with the first batch and closes when the last one in flight settles. It runs on
 * {@link UMBRELLA_LANE}, never the batches' own lane, which it would otherwise throttle while waiting
 * on them. Module-scoped for the same reason as {@link batchSequence}.
 */
let wave: { id: ActivityId; pending: number; close: () => void; closing?: ReturnType<typeof setTimeout> } | undefined;
let waveSequence = 0;

/**
 * How long the umbrella stays open after its last batch settles. The item cache sends batches one
 * after another with a debounce between them, so closing at once would open a new umbrella, and a
 * new row, for every batch again.
 */
const WAVE_GRACE_MS = 3000;

export const useHistoricPriceCache = createSharedComposable((): UseHistoricPriceCacheReturn => {
  const currencySymbol = useSetting('currencySymbol');
  const historicCachePriceStore = useHistoricCachePriceStore();
  const { historicStorage } = historicCachePriceStore;
  const { failedDailyPrices, historicalDailyPriceStatus, resolvedFailedDailyPrices } = storeToRefs(historicCachePriceStore);
  const { queryHistoricalRates } = usePriceApi();
  const { cancelByPrefix, submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  const createKey = (fromAsset: string, timestamp: number | string): string => `${fromAsset}#${timestamp}`;

  /** Joins the umbrella in flight, opening one first when none is, and returns its id as the parent. */
  function joinWave(): ActivityId {
    if (!wave) {
      let close!: () => void;
      const settled = new Promise<void>((resolve) => {
        close = resolve;
      });
      const id = makeActivityId(ActivityKind.PRICES, ActivityPart.HISTORIC, ActivityPart.BATCH, 'all', ++waveSequence);
      wave = { close, id, pending: 0 };
      startPromise(submitTask({
        id,
        kind: ActivityKind.PRICES,
        lane: UMBRELLA_LANE,
        rerunnable: false,
        run: async (): Promise<Result<void, TaskError>> => {
          await settled;
          return ok(undefined);
        },
        subtitle: t('task_center.activity.prices.historic_batches', { toAsset: get(currencySymbol) }),
        title: t('task_center.group.prices'),
      }));
    }
    clearTimeout(wave.closing);
    wave.pending += 1;
    return wave.id;
  }

  /** Leaves the umbrella, closing it a grace period after its last batch has settled. */
  function leaveWave(id: ActivityId): void {
    const current = wave;
    if (current?.id !== id)
      return;
    current.pending -= 1;
    if (current.pending > 0)
      return;
    current.closing = setTimeout(() => {
      if (wave !== current || current.pending > 0)
        return;
      current.close();
      wave = undefined;
    }, WAVE_GRACE_MS);
  }

  async function fetchHistoricPrices(keys: string[]): ReturnType<Parameters<typeof createItemCache<BigNumber>>[0]> {
    const assetsTimestamp = keys.map((key) => {
      const [from, timestamp] = key.split('#');

      return [from, timestamp];
    });
    const targetAsset = get(currencySymbol);
    const description = t(
      'actions.balances.historic_fetch_price.task.description',
      {
        count: assetsTimestamp.length,
        toAsset: targetAsset,
      },
      2,
    );

    const parent = joinWave();
    const outcome = await submitTask<HistoricPrices>({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.HISTORIC, ActivityPart.BATCH, ++batchSequence),
      kind: ActivityKind.PRICES,
      parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<HistoricPrices, TaskError>> => mapResult(
        await runTask<HistoricPrices>(
          async () => queryHistoricalRates({
            assetsTimestamp,
            targetAsset,
          }),
        ),
        result => result,
      ),
      subtitle: description,
      title: t('task_center.group.prices'),
    }).finally(() => leaveWave(parent));

    const response = HistoricPrices.parse(getOr(outcome, { assets: {}, targetAsset: '' }));

    return function* (): Generator<{ key: string; item: BigNumber }, void> {
      for (const assetTimestamp of assetsTimestamp) {
        const [fromAsset, timestamp] = assetTimestamp;
        const key = createKey(fromAsset, timestamp);

        const item = response.assets?.[fromAsset]?.[timestamp];
        yield { item, key };
      }
    };
  }

  const {
    cache,
    deleteCacheKeys,
    getIsPending,
    isPending,
    reset,
    resolve,
    unknown,
  } = createItemCache<BigNumber>(async keys => fetchHistoricPrices(keys), {
    label: 'historic-price',
    maxSize: 5000,
    size: 500,
    storage: historicStorage,
  });

  function getHistoricPrice(fromAsset: string, timestamp: number): BigNumber {
    const key = createKey(fromAsset, timestamp);

    if (getIsPending(key))
      return NoPrice;

    return resolve(key) ?? NoPrice;
  }

  function historicPriceInCurrentCurrency(fromAsset: string, timestamp: number): ComputedRef<BigNumber> {
    return computed<BigNumber>(() => getHistoricPrice(fromAsset, timestamp));
  }

  /**
   * Drops the cached prices an edited item invalidates, itself and its neighbours within the hour.
   *
   * @remarks
   * A price is cached against the exact timestamp it was asked for, but callers ask for whatever
   * timestamp their event carries. Editing one price therefore has to clear the near-misses too,
   * or a lookup a few minutes either side keeps answering with the old figure.
   */
  function resetHistoricalPricesData(items: { fromAsset: string; timestamp: number }[]): void {
    const keysToBeDeleted = new Set<string>();
    const cacheKeys = Object.keys(get(cache));
    const unknownKeys = unknown.keys();

    const isWithinAnHour = (cacheKey: string, fromAsset: string, targetTime: number): boolean => {
      const [cacheAsset, cacheTimestamp] = cacheKey.split('#');
      const cacheTime = parseInt(cacheTimestamp, 10);

      return cacheAsset === fromAsset && Math.abs(cacheTime - targetTime) <= SECONDS_PER_HOUR;
    };

    items.forEach(({ fromAsset, timestamp }) => {
      [...cacheKeys, ...unknownKeys]
        .filter(cacheKey => isWithinAnHour(cacheKey, fromAsset, timestamp))
        .forEach(cacheKey => keysToBeDeleted.add(cacheKey));
    });

    deleteCacheKeys([...keysToBeDeleted]);
  }

  /**
   * Drops every cached and in-flight historic price after a currency change.
   *
   * @remarks
   * Everything already fetched or still in flight is quoted in the old currency, so none of it
   * can be reused. Cancelling by prefix rather than by id is what reaches all of it: each query
   * and each batch carries an id of its own.
   */
  function discardPricesInOldCurrency(): void {
    cancelByPrefix(ActivityKind.PRICES, ActivityPart.HISTORIC);
    cancelByPrefix(ActivityKind.PRICES, ActivityPart.DAILY);
    set(failedDailyPrices, {});
    set(resolvedFailedDailyPrices, {});
    reset();
  }

  watch(currencySymbol, discardPricesInOldCurrency);

  /** The cache lives outside the store state, so the store reset at logout does not reach it. */
  onSessionCleared('historic-price-cache', reset);

  return {
    cache,
    createKey,
    failedDailyPrices,
    getHistoricPrice,
    getIsPending,
    historicalDailyPriceStatus,
    historicPriceInCurrentCurrency,
    isPending,
    resolvedFailedDailyPrices,
    reset,
    resetHistoricalPricesData,
    resolve,
    unknown,
  };
});
