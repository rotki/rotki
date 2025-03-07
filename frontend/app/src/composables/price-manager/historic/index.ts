import type { HistoricalPrice, HistoricalPriceFormPayload, ManualPricePayload } from '@/types/prices';
import type { Ref } from 'vue';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { NotificationCategory, type NotificationPayload, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';

interface UseHistoricPricesReturn {
  items: Ref<HistoricalPrice[]>;
  loading: Ref<boolean>;
  save: (data: HistoricalPriceFormPayload, update: boolean) => Promise<boolean>;
  deletePrice: (item: HistoricalPrice) => Promise<void>;
  refresh: (payload?: { modified?: boolean; additionalEntry?: HistoricalPrice }) => Promise<void>;
}

export function useHistoricPrices(
  t: ReturnType<typeof useI18n>['t'],
  filter?: Ref<{ fromAsset?: string; toAsset?: string }>,
): UseHistoricPricesReturn {
  const loading = ref(false);
  const items = ref<HistoricalPrice[]>([]);

  const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();
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
        category: NotificationCategory.DEFAULT,
        display: true,
        message: t('price_table.fetch.failure.message', {
          message: error.message,
        }),
        severity: Severity.ERROR,
        title: t('price_table.fetch.failure.title'),
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
        description,
        success: false,
        title,
      });

      return false;
    }
  };

  const deletePrice = async (item: HistoricalPrice): Promise<void> => {
    const { price, ...payload } = item;
    try {
      await deleteHistoricalPrice(payload);
      await refresh({
        additionalEntry: item,
        modified: true,
      });
    }
    catch (error: any) {
      const notification: NotificationPayload = {
        category: NotificationCategory.DEFAULT,
        display: true,
        message: t('price_table.delete.failure.message', {
          message: error.message,
        }),
        severity: Severity.ERROR,
        title: t('price_table.delete.failure.title'),
      };
      notify(notification);
    }
  };

  if (filter) {
    watch(
      filter,
      async () => {
        await refresh();
      },
      { deep: true },
    );
  }

  onBeforeMount(() => {
    startPromise(refresh());
  });

  return {
    deletePrice,
    items,
    loading,
    refresh,
    save,
  };
}
