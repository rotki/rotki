import { NotificationCategory, type NotificationPayload, Severity } from '@rotki/common';
import type { HistoricalPrice, HistoricalPriceFormPayload, ManualPricePayload } from '@/types/prices';

interface UseHistoricPricesReturn {
  items: Ref<HistoricalPrice[]>;
  loading: Ref<boolean>;
  save: (data: HistoricalPriceFormPayload, update: boolean) => Promise<boolean>;
  deletePrice: (item: HistoricalPrice) => Promise<void>;
  refresh: (payload?: { modified?: boolean; additionalEntry?: HistoricalPrice }) => Promise<void>;
}

export function useHistoricPrices(
  filter: Ref<{ fromAsset?: string; toAsset?: string }>,
  t: ReturnType<typeof useI18n>['t'],
): UseHistoricPricesReturn {
  const loading = ref(false);
  const items = ref<HistoricalPrice[]>([]);

  const { editHistoricalPrice, addHistoricalPrice, fetchHistoricalPrices, deleteHistoricalPrice } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricCachePriceStore();
  const { setMessage } = useMessageStore();
  const { notify } = useNotificationsStore();

  const fetchPrices = async (payload?: Partial<ManualPricePayload>): Promise<void> => {
    set(loading, true);
    try {
      set(items, await fetchHistoricalPrices(payload));
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

  const refresh = async (payload?: { modified?: boolean; additionalEntry?: HistoricalPrice }): Promise<void> => {
    await fetchPrices(get(filter));

    if (payload?.modified) {
      const entries: HistoricalPrice[] = [...get(items)];
      if (payload?.additionalEntry)
        entries.push(payload.additionalEntry);

      resetHistoricalPricesData(entries);
    }
  };

  const save = async (data: HistoricalPriceFormPayload, update: boolean): Promise<boolean> => {
    try {
      if (update)
        return await editHistoricalPrice(data);

      return await addHistoricalPrice(data);
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

  const deletePrice = async (item: HistoricalPrice): Promise<void> => {
    const { price, ...payload } = item;
    try {
      await deleteHistoricalPrice(payload);
      await refresh({
        modified: true,
        additionalEntry: item,
      });
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

  watch(
    filter,
    async () => {
      await refresh();
    },
    { deep: true },
  );

  onBeforeMount(() => {
    startPromise(refresh());
  });

  return {
    items,
    loading,
    save,
    deletePrice,
    refresh,
  };
}
