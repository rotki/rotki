import type { Ref } from 'vue';
import type { HistoricalPrice, HistoricalPriceFormPayload, ManualPricePayload } from '@/modules/prices/price-types';
import { startPromise } from '@shared/utils';
import { useAssetPricesApi } from '@/composables/api/assets/prices';
import { getErrorMessage } from '@/modules/common/logging/error-handling';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useHistoricPriceCache } from '@/modules/prices/use-historic-price-cache';

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
  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { notifyError, showErrorMessage } = useNotifications();

  const fetchPrices = async (payload?: Partial<ManualPricePayload>): Promise<void> => {
    set(loading, true);
    try {
      set(items, await fetchHistoricalPrices(payload));
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

  const deletePrice = async (item: HistoricalPrice): Promise<void> => {
    const { price, ...payload } = item;
    try {
      await deleteHistoricalPrice(payload);
      await refresh({
        additionalEntry: item,
        modified: true,
      });
    }
    catch (error: unknown) {
      notifyError(
        t('price_table.delete.failure.title'),
        t('price_table.delete.failure.message', { message: getErrorMessage(error) }),
      );
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
