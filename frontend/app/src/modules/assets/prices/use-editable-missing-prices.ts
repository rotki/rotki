import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalPrice, HistoricalPriceDeletePayload, HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import type { EditableMissingPrice, MissingPrice } from '@/modules/reports/report-types';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { PriceOracle } from '@/modules/settings/types/price-oracle';

interface UseEditableMissingPricesOptions {
  /** The prices the report or the dialog could not resolve. */
  items: MaybeRefOrGetter<MissingPrice[]>;
  /**
   * Identifies a row in the error and refreshed-price maps.
   *
   * @remarks
   * The two callers key differently: a report holds several assets at once and needs the whole
   * triple, while a single-asset dialog only needs the timestamp.
   */
  keyOf: (item: MissingPrice) => string;
  /** Called after a row's price is written, for bookkeeping the caller owns. */
  onPriceUpdated?: (item: EditableMissingPrice) => void;
}

interface UseEditableMissingPricesReturn {
  /** Forgets the failure shown on a row, once the user starts correcting it. */
  clearError: (item: MissingPrice) => void;
  /** Validation and lookup failures, keyed by {@link UseEditableMissingPricesOptions.keyOf}. */
  errorMessages: Readonly<Ref<Record<string, string>>>;
  /** The rows, each carrying whatever price is already known for it. */
  formattedItems: ComputedRef<EditableMissingPrice[]>;
  /** Re-reads the manually saved prices. */
  getHistoricalPrices: () => Promise<void>;
  /** Whether an oracle lookup is in flight. */
  refreshing: Readonly<Ref<boolean>>;
  /**
   * Asks the oracles for a rate the report could not find.
   *
   * @remarks
   * A rate of zero counts as not found, and is reported on the row rather than saved.
   */
  refreshHistoricalPrice: (item: EditableMissingPrice) => Promise<void>;
  /**
   * Writes a row's price: adds, edits, or deletes the manual price to match what was typed.
   *
   * @remarks
   * A row showing a rate fetched from an oracle is left alone; that price was never the user's to
   * save. An empty price on a saved row deletes it.
   */
  updatePrice: (item: EditableMissingPrice) => Promise<void>;
}

/**
 * Drives an editable table of prices rotki could not resolve, shared by the profit and loss
 * report's missing-prices pane and the failed-daily-prices dialog.
 *
 * @returns the rows and the two things a user can do to one
 */
export function useEditableMissingPrices(options: UseEditableMissingPricesOptions): UseEditableMissingPricesReturn {
  const { items, keyOf, onPriceUpdated } = options;

  const { t } = useI18n({ useScope: 'global' });

  const prices = ref<HistoricalPrice[]>([]);
  const errorMessages = ref<Record<string, string>>({});
  const refreshedHistoricalPrices = ref<Record<string, BigNumber>>({});
  const refreshing = shallowRef<boolean>(false);

  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();
  const { getHistoricPrice } = usePriceTaskManager();

  const formattedItems = computed<EditableMissingPrice[]>(() =>
    toValue(items).map((item) => {
      const savedHistoricalPrice = get(prices).find(
        price => price.fromAsset === item.fromAsset && price.toAsset === item.toAsset && price.timestamp === item.time,
      );

      const savedPrice = savedHistoricalPrice?.price;
      const refreshedHistoricalPrice = get(refreshedHistoricalPrices)[keyOf(item)];

      const useRefreshedHistoricalPrice = !savedPrice && !!refreshedHistoricalPrice;

      const price = (useRefreshedHistoricalPrice ? refreshedHistoricalPrice : savedPrice)?.toFixed() ?? '';

      return {
        ...item,
        price,
        saved: !!savedPrice,
        useRefreshedHistoricalPrice,
      };
    }),
  );

  async function getHistoricalPrices(): Promise<void> {
    set(prices, await fetchHistoricalPrices());
  }

  function reportOn(item: MissingPrice, message: string): void {
    set(errorMessages, {
      ...get(errorMessages),
      [keyOf(item)]: message,
    });
  }

  function clearError(item: MissingPrice): void {
    const { [keyOf(item)]: cleared, ...rest } = get(errorMessages);
    if (cleared !== undefined)
      set(errorMessages, rest);
  }

  async function writePrice(item: EditableMissingPrice, payload: HistoricalPriceDeletePayload): Promise<void> {
    if (item.price) {
      const formPayload: HistoricalPriceFormPayload = {
        ...payload,
        price: item.price,
      };

      if (item.saved)
        await editHistoricalPrice(formPayload);
      else await addHistoricalPrice(formPayload);
    }
    else if (item.saved) {
      await deleteHistoricalPrice(payload);
    }
  }

  async function updatePrice(item: EditableMissingPrice): Promise<void> {
    if (item.useRefreshedHistoricalPrice)
      return;

    const payload: HistoricalPriceDeletePayload = {
      fromAsset: item.fromAsset,
      sourceType: PriceOracle.MANUAL,
      timestamp: item.time,
      toAsset: item.toAsset,
    };

    try {
      await writePrice(item, payload);
    }
    catch (error: unknown) {
      let errorMessage = getErrorMessage(error);
      if (error instanceof ApiValidationError) {
        const errors = error.getValidationErrors({ price: '' });
        errorMessage = typeof errors === 'string' ? error.message : errors.price[0];
      }

      reportOn(item, errorMessage);
    }

    resetHistoricalPricesData([payload]);
    onPriceUpdated?.(item);

    await getHistoricalPrices();
  }

  async function refreshHistoricalPrice(item: EditableMissingPrice): Promise<void> {
    set(refreshing, true);
    const rateFromHistoricPrice = await getHistoricPrice({
      fromAsset: item.fromAsset,
      timestamp: item.time,
      toAsset: item.toAsset,
    });

    if (rateFromHistoricPrice?.gt(0)) {
      set(refreshedHistoricalPrices, {
        ...get(refreshedHistoricalPrices),
        [keyOf(item)]: rateFromHistoricPrice,
      });
    }
    else {
      reportOn(item, t('profit_loss_report.actionable.missing_prices.price_not_found'));
    }
    set(refreshing, false);
  }

  return {
    clearError,
    errorMessages: readonly(errorMessages),
    formattedItems,
    getHistoricalPrices,
    refreshHistoricalPrice,
    refreshing: readonly(refreshing),
    updatePrice,
  };
}
