import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ManualPrice, ManualPriceFormPayload, ManualPriceWithUsd } from '@/modules/assets/prices/price-types';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { type BigNumber, Zero } from '@rotki/common';
import { isErr, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { isNft } from '@/modules/assets/nft-utils';
import { usePriceRefresh } from '@/modules/assets/prices/use-price-refresh';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseLatestPricesReturn {
  items: ComputedRef<ManualPriceWithUsd[]>;
  loading: Readonly<Ref<boolean>>;
  refreshing: Readonly<Ref<boolean>>;
  getLatestPrices: () => Promise<void>;
  save: (data: ManualPriceFormPayload, update: boolean) => Promise<boolean>;
  refreshCurrentPrices: (additionalAssets?: string[]) => Promise<void>;
  deletePrice: ({ fromAsset }: { fromAsset: string }) => Promise<void>;
}

export function useLatestPrices(
  t: ReturnType<typeof useI18n>['t'],
  filter?: MaybeRefOrGetter<string | undefined>,
): UseLatestPricesReturn {
  const latestPrices = ref<ManualPrice[]>([]);
  const loading = shallowRef<boolean>(false);
  const refreshing = shallowRef<boolean>(false);

  const { addLatestPrice, deleteLatestPrice, fetchLatestPrices } = useAssetPricesApi();
  const { getAssetPrice } = usePriceUtils();
  const { refreshPrices } = usePriceRefresh();
  const { notifyError, showErrorMessage } = useNotifications();
  const { submitTask } = useNativeTask();

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

  const getLatestPrices = async (): Promise<void> => {
    set(loading, true);
    try {
      set(latestPrices, await fetchLatestPrices());
    }
    catch (error: unknown) {
      notifyError(
        t('price_table.fetch.failure.title'),
        t('price_table.fetch.failure.message', { message: getErrorMessage(error) }),
      );
    }
    finally {
      set(loading, false);
    }
  };

  /**
   * Saves a manually entered price.
   *
   * @remarks
   * Runs under its own `prices:manual:add` activity so that consumers priced off manual values,
   * such as NFT balances, can declare themselves stale after a hand edit without also firing on
   * every automatic price sweep.
   *
   * Pass `update` true to overwrite an existing manual price, false to add a new one.
   *
   * @returns whether the price was saved
   */
  const save = async (data: ManualPriceFormPayload, update: boolean): Promise<boolean> => {
    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.MANUAL, ActivityPart.ADD),
      kind: ActivityKind.PRICES,
      rerunnable: false,
      run: async (): Promise<Result<boolean, TaskError>> => ok(await addLatestPrice(data)),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.manual_add'), { asset: data.fromAsset }),
      title: t('task_center.group.prices'),
    });

    if (!isErr(outcome))
      return outcome.value;

    const values = { message: outcome.error.message };
    const title = update ? t('price_management.edit.error.title') : t('price_management.add.error.title');
    const description = update
      ? t('price_management.edit.error.description', values)
      : t('price_management.add.error.description', values);

    showErrorMessage(title, description);
    return false;
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
      id: makeActivityId(ActivityKind.PRICES, ActivityPart.MANUAL, ActivityPart.REMOVE),
      kind: ActivityKind.PRICES,
      rerunnable: false,
      run: async (): Promise<Result<void, TaskError>> => {
        await deleteLatestPrice(fromAsset);
        return ok(undefined);
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.manual_remove'), { asset: fromAsset }),
      title: t('task_center.group.prices'),
    });

    if (isErr(outcome)) {
      notifyError(
        t('price_table.delete.failure.title'),
        t('price_table.delete.failure.message', { message: outcome.error.message }),
      );
      return;
    }

    await refreshCurrentPrices([fromAsset]);
  };

  return {
    deletePrice,
    getLatestPrices,
    items,
    loading: readonly(loading),
    refreshCurrentPrices,
    refreshing: readonly(refreshing),
    save,
  };
}
