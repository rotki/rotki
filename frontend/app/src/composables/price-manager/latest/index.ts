import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { ManualPrice, ManualPriceFormPayload, ManualPriceWithUsd } from '@/modules/prices/price-types';
import { Zero } from '@rotki/common';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useStatusUpdater } from '@/composables/status';
import { CURRENCY_USD } from '@/modules/amount-display/currencies';
import { isNft } from '@/modules/assets/nft-utils';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { Section } from '@/modules/common/status';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { usePriceRefresh } from '@/modules/prices/use-price-refresh';
import { usePriceUtils } from '@/modules/prices/use-price-utils';

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
  const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);
  const { notifyError, showErrorMessage } = useNotifications();

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
      const priceInCurrency = isNft(fromAsset)
        ? getAssetPrice(toAsset)?.multipliedBy(price)
        : getAssetPrice(fromAsset);

      return {
        id: index + 1,
        ...item,
        usdPrice: priceInCurrency || Zero,
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

  const save = async (data: ManualPriceFormPayload, update: boolean): Promise<boolean> => {
    try {
      return await addLatestPrice(data);
    }
    catch (error: unknown) {
      const values = { message: getErrorMessage(error) };
      const title = update ? t('price_management.edit.error.title') : t('price_management.add.error.title');
      const description = update
        ? t('price_management.edit.error.description', values)
        : t('price_management.add.error.description', values);

      showErrorMessage(title, description);
      return false;
    }
  };

  const refreshCurrentPrices = async (additionalAssets: string[] = []): Promise<void> => {
    await getLatestPrices();
    set(refreshing, true);
    const assetToRefresh = [...get(latestAssets), ...additionalAssets];
    await refreshPrices(false, assetToRefresh);
    resetStatus();
    set(refreshing, false);
  };

  const deletePrice = async ({ fromAsset }: { fromAsset: string }): Promise<void> => {
    try {
      await deleteLatestPrice(fromAsset);
      await refreshCurrentPrices([fromAsset]);
    }
    catch (error: unknown) {
      notifyError(
        t('price_table.delete.failure.title'),
        t('price_table.delete.failure.message', { message: getErrorMessage(error) }),
      );
    }
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
