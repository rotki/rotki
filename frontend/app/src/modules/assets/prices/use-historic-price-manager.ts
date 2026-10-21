import type { MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalPrice, HistoricalPriceFormPayload, ManualPricePayload } from '@/modules/assets/prices/price-types';
import { startPromise } from '@shared/utils';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface UseHistoricPricesReturn {
  items: Readonly<Ref<HistoricalPrice[]>>;
  loading: Readonly<Ref<boolean>>;
  save: (data: HistoricalPriceFormPayload, update: boolean) => Promise<boolean>;
  deletePrice: (item: HistoricalPrice) => Promise<void>;
  refresh: (payload?: { modified?: boolean; additionalEntry?: HistoricalPrice }) => Promise<void>;
}

export function useHistoricPrices(
  t: ReturnType<typeof useI18n>['t'],
  filter?: MaybeRefOrGetter<{ fromAsset?: string; toAsset?: string }>,
): UseHistoricPricesReturn {
  const loading = shallowRef(false);
  const items = ref<HistoricalPrice[]>([]);

  const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { notifyError, notifyFailure, showErrorMessage } = useNotifications();
  const { resolveMissingPrice } = useBackendProblemsStore();

  const fetchPrices = async (payload?: Partial<ManualPricePayload>): Promise<void> => {
    set(loading, true);
    try {
      set(items, await fetchHistoricalPrices(payload));
    }
    catch (error: unknown) {
      notifyFailure(
        t('price_table.fetch.failure.title'),
        t('price_table.fetch.failure.message', { message: getErrorMessage(error) }),
      );
    }
    finally {
      set(loading, false);
    }
  };

  const refresh = async (payload?: { modified?: boolean; additionalEntry?: HistoricalPrice }): Promise<void> => {
    await fetchPrices(toValue(filter));

    if (payload?.modified) {
      const entries: HistoricalPrice[] = [...get(items)];
      if (payload?.additionalEntry)
        entries.push(payload.additionalEntry);

      resetHistoricalPricesData(entries);
    }
  };

  /**
   * Saves a manual historic price.
   *
   * @remarks
   * A saved price fixes the backend's missing-price report for that asset and time, so its item
   * leaves the notification drawer rather than asking for a price the user has just added.
   */
  const save = async (data: HistoricalPriceFormPayload, update: boolean): Promise<boolean> => {
    try {
      const saved = update ? await editHistoricalPrice(data) : await addHistoricalPrice(data);
      if (saved)
        resolveMissingPrice(data.fromAsset, data.timestamp);

      return saved;
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
      await deleteHistoricalPrice({ ...payload, sourceType: PriceOracle.MANUAL });
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
      () => toValue(filter),
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
    items: shallowReadonly(items),
    loading: readonly(loading),
    refresh,
    save,
  };
}
