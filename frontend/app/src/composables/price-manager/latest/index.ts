import {
  NotificationCategory,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import { omit } from 'lodash-es';
import { type Nullable } from '@rotki/common';
import { type ManualPrice, type ManualPriceFormPayload } from '@/types/prices';
import { Section } from '@/types/status';
import { CURRENCY_USD } from '@/types/currencies';
import { isNft } from '@/utils/nft';

export const useLatestPrices = (
  t: ReturnType<typeof useI18n>['t'],
  filter?: Ref<Nullable<string>>
) => {
  const latestPrices = ref<ManualPrice[]>([]);
  const loading = ref(false);
  const refreshing = ref(false);

  const { deleteLatestPrice, fetchLatestPrices, addLatestPrice } =
    useAssetPricesApi();
  const { assetPrice } = useBalancePricesStore();
  const { assets } = useAggregatedBalances();
  const { refreshPrices } = useBalances();
  const { resetStatus } = useStatusUpdater(Section.NON_FUNGIBLE_BALANCES);
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();

  const latestAssets: ComputedRef<string[]> = computed(() =>
    get(latestPrices)
      .flatMap(({ fromAsset, toAsset }) => [fromAsset, toAsset])
      .filter(asset => asset !== CURRENCY_USD)
  );

  const items = computed(() => {
    const filterVal = get(filter);
    const latestPricesVal = get(latestPrices);

    const filteredItems = filterVal
      ? latestPricesVal.filter(({ fromAsset }) => fromAsset === filterVal)
      : latestPricesVal;

    return filteredItems.map(item => ({
      ...item,
      usdPrice: !isNft(item.fromAsset)
        ? get(assetPrice(item.fromAsset))
        : (get(assetPrice(item.toAsset)) ?? One).multipliedBy(item.price)
    }));
  });

  const getLatestPrices = async () => {
    set(loading, true);
    try {
      set(latestPrices, await fetchLatestPrices());
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: t('price_table.fetch.failure.title'),
        message: t('price_table.fetch.failure.message', {
          message: e.message
        }),
        display: true,
        severity: Severity.ERROR,
        category: NotificationCategory.DEFAULT
      };
      notify(notification);
    } finally {
      set(loading, false);
    }
  };

  const save = async (
    data: ManualPriceFormPayload,
    update: boolean
  ): Promise<boolean> => {
    try {
      return await addLatestPrice(omit(data, 'usdPrice'));
    } catch (e: any) {
      const values = { message: e.message };
      const title = update
        ? t('price_management.edit.error.title')
        : t('price_management.add.error.title');
      const description = update
        ? t('price_management.edit.error.description', values)
        : t('price_management.add.error.description', values);

      setMessage({
        title,
        description,
        success: false
      });
      return false;
    }
  };

  const deletePrice = async (
    { fromAsset }: { fromAsset: string },
    refetch: boolean = false
  ) => {
    try {
      await deleteLatestPrice(fromAsset);
      if (refetch) {
        await getLatestPrices();
      }
      await refreshCurrentPrices(true);
    } catch (e: any) {
      const notification: NotificationPayload = {
        title: t('price_table.delete.failure.title'),
        message: t('price_table.delete.failure.message', {
          message: e.message
        }),
        display: true,
        severity: Severity.ERROR,
        category: NotificationCategory.DEFAULT
      };
      notify(notification);
    }
  };

  const refreshCurrentPrices = async (refreshAll: boolean = false) => {
    set(refreshing, true);
    const assetToRefresh = [...get(latestAssets)];
    if (refreshAll) {
      assetToRefresh.push(...get(assets()));
    }
    await refreshPrices(false, assetToRefresh);
    resetStatus();
    set(refreshing, false);
  };

  return {
    items,
    loading,
    refreshing,
    getLatestPrices,
    save,
    refreshCurrentPrices,
    deletePrice
  };
};
