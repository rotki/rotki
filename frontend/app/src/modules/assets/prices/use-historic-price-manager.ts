import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalPrice, HistoricalPriceFormPayload, ManualPricePayload } from '@/modules/assets/prices/price-types';
import { startPromise } from '@shared/utils';
import { err, ok, type Result } from 'plainfp/result';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useBackendProblemsStore } from '@/modules/core/notifications/problems/use-backend-problems-store';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type TableEmptyState, useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface UseHistoricPricesReturn {
  items: Readonly<Ref<HistoricalPrice[]>>;
  /** The table's empty text, or why the last fetch failed: the table is the only place that says so. */
  emptyState: ComputedRef<TableEmptyState>;
  loading: Readonly<Ref<boolean>>;
  save: (data: HistoricalPriceFormPayload, update: boolean) => Promise<Result<boolean, unknown>>;
  deletePrice: (item: HistoricalPrice) => Promise<void>;
  refresh: (payload?: { modified?: boolean; additionalEntry?: HistoricalPrice }) => Promise<void>;
}

/**
 * The manual historic prices, and saving or deleting one.
 *
 * @remarks
 * The list loads only for a caller that passes a filter, as the price table does, and reloads when
 * it changes. A caller without one, like the price form, only saves and deletes.
 *
 * @param filter - the pair the list is narrowed to; an empty object lists every price
 */
export function useHistoricPrices(
  filter?: MaybeRefOrGetter<{ fromAsset?: string; toAsset?: string }>,
): UseHistoricPricesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const loading = shallowRef<boolean>(false);
  const items = ref<HistoricalPrice[]>([]);
  const fetchError = shallowRef<unknown>();

  const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { notifyError } = useNotifications();
  const { resolveMissingPrice } = useBackendProblemsStore();
  const emptyState = useTableEmptyState({ error: fetchError });

  /** A failure empties the list and is shown by the table through `emptyState`, so it files no notification. */
  const fetchPrices = async (payload?: Partial<ManualPricePayload>): Promise<void> => {
    set(loading, true);
    set(fetchError, undefined);
    try {
      set(items, await fetchHistoricalPrices(payload));
    }
    catch (error: unknown) {
      if (!isRequestCancellation(error)) {
        logger.error(error);
        set(items, []);
        set(fetchError, error);
      }
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
   * leaves the notification drawer rather than asking for a price the user has just added. A failure
   * is handed back for the open form to name.
   *
   * @returns whether the price was saved, or why it could not be
   */
  const save = async (data: HistoricalPriceFormPayload, update: boolean): Promise<Result<boolean, unknown>> => {
    try {
      const saved = update ? await editHistoricalPrice(data) : await addHistoricalPrice(data);
      if (saved)
        resolveMissingPrice(data.fromAsset, data.timestamp);

      return ok(saved);
    }
    catch (error: unknown) {
      logger.error('Failed to save a historic price:', error);
      return err(error);
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

    onBeforeMount(() => {
      startPromise(refresh());
    });
  }

  return {
    deletePrice,
    emptyState,
    items: shallowReadonly(items),
    loading: readonly(loading),
    refresh,
    save,
  };
}
