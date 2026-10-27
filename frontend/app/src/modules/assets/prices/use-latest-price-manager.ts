import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ManualPrice, ManualPriceFormPayload, ManualPriceWithUsd } from '@/modules/assets/prices/price-types';
import { type BigNumber, Zero } from '@rotki/common';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { isNft } from '@/modules/assets/nft-utils';
import { manualPriceAddActivity, manualPriceRemoveActivity } from '@/modules/assets/prices/prices.activity';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { logger } from '@/modules/core/common/logging/logging';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { type TableEmptyState, useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseLatestPricesReturn {
  items: ComputedRef<ManualPriceWithUsd[]>;
  /** The table's empty text, or why the last fetch failed: the table is the only place that says so. */
  emptyState: ComputedRef<TableEmptyState>;
  loading: Readonly<Ref<boolean>>;
  refreshing: Readonly<Ref<boolean>>;
  getLatestPrices: () => Promise<void>;
  save: (data: ManualPriceFormPayload) => Promise<Result<boolean, TaskError>>;
  refreshCurrentPrices: (additionalAssets?: string[]) => Promise<void>;
  deletePrice: ({ fromAsset }: { fromAsset: string }) => Promise<void>;
}

export function useLatestPrices(
  filter?: MaybeRefOrGetter<string | undefined>,
): UseLatestPricesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const latestPrices = ref<ManualPrice[]>([]);
  const loading = shallowRef<boolean>(false);
  const refreshing = shallowRef<boolean>(false);
  const fetchError = shallowRef<unknown>();

  const { addLatestPrice, deleteLatestPrice, fetchLatestPrices } = useAssetPricesApi();
  const { getAssetPrice } = usePriceUtils();
  const { refreshPrices } = usePriceRefresh();
  const { submitTask } = useNativeTask();
  const { resolveMissingCurrentPrice } = useBackendProblemsStore();
  const emptyState = useTableEmptyState({ error: fetchError });

  const latestAssets = computed<string[]>(() =>
    get(latestPrices)
      .flatMap(({ fromAsset, toAsset }) => [fromAsset, toAsset])
      .filter(asset => asset !== CURRENCY_USD),
  );

  const items = computed<ManualPriceWithUsd[]>(() => {
    const filterVal = get(filter);
    const latestPricesVal = get(latestPrices);

    const filteredItems = filterVal
      ? latestPricesVal.filter(({ fromAsset }) => fromAsset === filterVal)
      : latestPricesVal;

    return filteredItems.map((item, index) => {
      const { fromAsset, toAsset, price } = item;
      let priceInCurrency: BigNumber | undefined;
      if (isNft(fromAsset)) {
        const toPrice = getAssetPrice(toAsset);
        if (toPrice?.gt(0))
          priceInCurrency = toPrice.multipliedBy(price);
      }
      else {
        const fromPrice = getAssetPrice(fromAsset);
        if (fromPrice?.gt(0))
          priceInCurrency = fromPrice;
      }

      return {
        id: index + 1,
        ...item,
        usdPrice: priceInCurrency ?? Zero,
      } satisfies ManualPriceWithUsd;
    });
  });

  /**
   * Loads the manual latest prices.
   *
   * @remarks
   * A failure empties the list and is shown by the table through {@link UseLatestPricesReturn.emptyState},
   * so it files no notification. The asset page also calls this, through `refreshCurrentPrices`, only
   * to know which manual prices to refresh along with its asset; a failure there refreshes the asset
   * alone.
   */
  const getLatestPrices = async (): Promise<void> => {
    set(loading, true);
    set(fetchError, undefined);
    try {
      set(latestPrices, await fetchLatestPrices());
    }
    catch (error: unknown) {
      if (!isRequestCancellation(error)) {
        logger.error(error);
        set(latestPrices, []);
        set(fetchError, error);
      }
    }
    finally {
      set(loading, false);
    }
  };

  /**
   * Saves a manually entered price.
   *
   * @remarks
   * Runs under its own `prices:manual:add:<pair>` activity so that consumers priced off manual values,
   * such as NFT balances, can declare themselves stale after a hand edit without also firing on
   * every automatic price sweep.
   *
   * A failure also shows in the task's dock row; it is handed back so the open form can name it
   * too. A cancelled task hands back an ok `false`, as there is nothing to name.
   *
   * @returns whether the price was saved, or why it could not be
   */
  const save = async (data: ManualPriceFormPayload): Promise<Result<boolean, TaskError>> => {
    const outcome = await submitTask<boolean>({
      id: manualPriceAddActivity.id(data),
      kind: manualPriceAddActivity.kind,
      rerunnable: false,
      run: async (): Promise<Result<boolean, TaskError>> => ok(await addLatestPrice(data)),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.manual_add'), { asset: data.fromAsset }),
      title: t('task_center.group.prices'),
    });

    if (isErr(outcome))
      return isActionable(outcome.error) ? err(outcome.error) : ok(false);

    if (outcome.value)
      resolveMissingCurrentPrice(data.fromAsset);
    return ok(outcome.value);
  };

  const refreshCurrentPrices = async (additionalAssets: string[] = []): Promise<void> => {
    await getLatestPrices();
    set(refreshing, true);
    const assetToRefresh = [...get(latestAssets), ...additionalAssets];
    await refreshPrices(false, assetToRefresh);
    set(refreshing, false);
  };

  const deletePrice = async ({ fromAsset }: { fromAsset: string }): Promise<void> => {
    const outcome = await submitTask({
      id: manualPriceRemoveActivity.id({ fromAsset }),
      kind: manualPriceRemoveActivity.kind,
      rerunnable: false,
      run: async (): Promise<Result<void, TaskError>> => {
        await deleteLatestPrice(fromAsset);
        return ok(undefined);
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.manual_remove'), { asset: fromAsset }),
      title: t('task_center.group.prices'),
    });

    if (isErr(outcome))
      return;

    await refreshCurrentPrices([fromAsset]);
  };

  return {
    deletePrice,
    emptyState,
    getLatestPrices,
    items,
    loading: readonly(loading),
    refreshCurrentPrices,
    refreshing: readonly(refreshing),
    save,
  };
}
