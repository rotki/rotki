import {
  NotificationCategory,
  type NotificationPayload,
  Severity
} from '@rotki/common/lib/messages';
import {
  type HistoricalPrice,
  type HistoricalPriceFormPayload,
  type ManualPricePayload
} from '@/types/prices';

export const useHistoricPrices = (
  filter: Ref<{ fromAsset?: string; toAsset?: string }>,
  t: ReturnType<typeof useI18n>['t']
) => {
  const loading = ref(false);
  const items: Ref<HistoricalPrice[]> = ref([]);

  const {
    editHistoricalPrice,
    addHistoricalPrice,
    fetchHistoricalPrices,
    deleteHistoricalPrice
  } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricCachePriceStore();
  const { setMessage } = useMessageStore();
  const { notify } = useNotificationsStore();

  const fetchPrices = async (payload?: Partial<ManualPricePayload>) => {
    set(loading, true);
    try {
      set(items, await fetchHistoricalPrices(payload));
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

  const save = async (data: HistoricalPriceFormPayload, update: boolean) => {
    try {
      if (update) {
        return await editHistoricalPrice(data);
      }
      return await addHistoricalPrice(data);
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

  const deletePrice = async (item: HistoricalPrice) => {
    const { price, ...payload } = item!;
    try {
      await deleteHistoricalPrice(payload);
      await refresh({
        modified: true,
        additionalEntry: item
      });
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

  const refresh = async (payload?: {
    modified?: boolean;
    additionalEntry?: HistoricalPrice;
  }) => {
    await fetchPrices(get(filter));

    if (payload?.modified) {
      const entries: HistoricalPrice[] = [...get(items)];
      if (payload?.additionalEntry) {
        entries.push(payload.additionalEntry);
      }
      resetHistoricalPricesData(entries);
    }
  };

  watch(
    filter,
    async () => {
      await refresh();
    },
    { deep: true }
  );

  onBeforeMount(refresh);

  return {
    items,
    loading,
    save,
    deletePrice,
    refresh
  };
};
