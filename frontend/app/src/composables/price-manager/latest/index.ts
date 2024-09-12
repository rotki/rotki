import { NotificationCategory, type NotificationPayload, Severity } from '@rotki/common';
import { Section } from '@/types/status';
import { CURRENCY_USD } from '@/types/currencies';
import type { ManualPrice, ManualPriceFormPayload, ManualPriceWithUsd } from '@/types/prices';

interface UseLatestPricesReturn {
  items: ComputedRef<ManualPriceWithUsd[]>;
  loading: Ref<boolean>;
  refreshing: Ref<boolean>;
  getLatestPrices: () => Promise<void>;
  save: (data: ManualPriceFormPayload, update: boolean) => Promise<boolean>;
  refreshCurrentPrices: (additionalAssets?: string[]) => Promise<void>;
  deletePrice: ({ fromAsset }: { fromAsset: string }) => Promise<void>;
}

export function useLatestPrices(
  t: ReturnType<typeof useI18n>['t'],
  filter?: Ref<string | undefined>,
): UseLatestPricesReturn {
  const latestPrices = ref<ManualPrice[]>([]);
  const loading = ref(false);
  const refreshing = ref(false);

  const { deleteLatestPrice, fetchLatestPrices, addLatestPrice } = useAssetPricesApi();
  const { assetPrice } = useBalancePricesStore();
  const { refreshPrices } = useBalances();
  const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();

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

    return filteredItems.map(
      (item, index) =>
        ({
          id: index + 1,
          ...item,
          usdPrice:
            (!isNft(item.fromAsset)
              ? get(assetPrice(item.fromAsset))
              : (get(assetPrice(item.toAsset)) ?? One).multipliedBy(item.price)) || Zero,
        }) satisfies ManualPriceWithUsd,
    );
  });

  const getLatestPrices = async (): Promise<void> => {
    set(loading, true);
    try {
      set(latestPrices, await fetchLatestPrices());
    }
    catch (error: any) {
      const notification: NotificationPayload = {
        title: t('price_table.fetch.failure.title'),
        message: t('price_table.fetch.failure.message', {
          message: error.message,
        }),
        display: true,
        severity: Severity.ERROR,
        category: NotificationCategory.DEFAULT,
      };
      notify(notification);
    }
    finally {
      set(loading, false);
    }
  };

  const save = async (data: ManualPriceFormPayload, update: boolean): Promise<boolean> => {
    try {
      return await addLatestPrice(data);
    }
    catch (error: any) {
      const values = { message: error.message };
      const title = update ? t('price_management.edit.error.title') : t('price_management.add.error.title');
      const description = update
        ? t('price_management.edit.error.description', values)
        : t('price_management.add.error.description', values);

      setMessage({
        title,
        description,
        success: false,
      });
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
    catch (error: any) {
      const notification: NotificationPayload = {
        title: t('price_table.delete.failure.title'),
        message: t('price_table.delete.failure.message', {
          message: error.message,
        }),
        display: true,
        severity: Severity.ERROR,
        category: NotificationCategory.DEFAULT,
      };
      notify(notification);
    }
  };

  return {
    items,
    loading,
    refreshing,
    getLatestPrices,
    save,
    refreshCurrentPrices,
    deletePrice,
  };
}
