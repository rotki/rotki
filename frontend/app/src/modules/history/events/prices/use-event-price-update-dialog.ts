import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { OraclePriceEntry } from '@/modules/assets/prices/price-types';
import type { EventPriceUpdatePayload } from '@/modules/history/events/prices/use-event-price-update-trigger';
import { startPromise } from '@shared/utils';
import { parseNumericInput } from '@/modules/core/common/data/bignumbers';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { type EventPriceUpdateMode, useEventPriceUpdate } from '@/modules/history/events/prices/use-event-price-update';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useSetting } from '@/modules/settings/use-setting';

interface UseEventPriceUpdateDialogReturn {
  /** Closes the dialog without writing anything. */
  close: () => void;
  /** The price already recorded for this asset and moment, when one exists. */
  existingEntry: Readonly<Ref<OraclePriceEntry | undefined>>;
  /** True when the recorded price is one the user set by hand rather than an oracle's. */
  existingIsManual: ComputedRef<boolean>;
  /** True while the existing price is being read. */
  loading: Readonly<Ref<boolean>>;
  /** Whether the dialog is showing, derived from the payload it was handed. */
  open: ComputedRef<boolean>;
  /** Whether the new price is written as a manual entry or against the oracle. */
  modelMode: Ref<EventPriceUpdateMode>;
  /** The price as typed, before parsing. */
  modelPrice: Ref<string>;
  /** Validation messages for the price field; empty while it is untouched. */
  priceErrors: ComputedRef<string[]>;
  /** True when the typed price parses and is above zero. */
  priceValid: ComputedRef<boolean>;
  /**
   * Writes the price, then closes.
   *
   * @remarks
   * Writes nothing when the price has not actually changed, so re-opening a dialog and pressing
   * save cannot create a duplicate manual entry.
   */
  save: () => Promise<void>;
  /** True while the price is being written. */
  saving: Readonly<Ref<boolean>>;
  /** True when the user gets to choose between overwriting the oracle or adding a manual price. */
  showModeChoice: ComputedRef<boolean>;
}

/**
 * Drives the dialog that sets a historical price for one event's asset.
 *
 * @remarks
 * Reads whatever price is already recorded whenever the payload changes, so the field opens
 * pre-filled and the mode defaults to whichever kind that entry was.
 *
 * @param modelValue - the event being priced; undefined closes the dialog
 * @returns the dialog's bindings; only {@link UseEventPriceUpdateDialogReturn.save} writes
 */
export function useEventPriceUpdateDialog(
  modelValue: Ref<EventPriceUpdatePayload | undefined>,
): UseEventPriceUpdateDialogReturn {
  const modelPrice = shallowRef<string>('');
  const modelMode = shallowRef<EventPriceUpdateMode>('manual');
  const existingEntry = ref<OraclePriceEntry>();
  const loading = shallowRef<boolean>(false);
  const saving = shallowRef<boolean>(false);

  const { t } = useI18n({ useScope: 'global' });
  const { notifyError, notifyInfo } = useNotifications();
  const currencySymbol = useSetting('currencySymbol');
  const { fetchExistingEntry, updatePrice } = useEventPriceUpdate();

  const open = computed<boolean>(() => get(modelValue) !== undefined);

  function close(): void {
    set(modelValue, undefined);
  }

  const existingIsManual = computed<boolean>(() => get(existingEntry)?.sourceType === PriceOracle.MANUAL);
  const showModeChoice = computed<boolean>(() => Boolean(get(existingEntry)) && !get(existingIsManual));

  const parsedPrice = computed<BigNumber | undefined>(() => parseNumericInput(get(modelPrice).trim()));

  const priceValid = computed<boolean>(() => get(parsedPrice)?.isGreaterThan(0) ?? false);

  const priceErrors = computed<string[]>(() => {
    const value = get(modelPrice).trim();
    if (!value || get(priceValid))
      return [];
    return [t('event_asset_price_update.price_error')];
  });

  async function load(payload: EventPriceUpdatePayload): Promise<void> {
    set(loading, true);
    set(existingEntry, undefined);
    set(modelPrice, '');
    try {
      const entry = await fetchExistingEntry(payload.asset, get(currencySymbol), payload.timestamp);
      set(existingEntry, entry);
      if (entry) {
        set(modelPrice, entry.price.toFixed());
        set(modelMode, entry.sourceType === PriceOracle.MANUAL ? 'manual' : 'oracle');
      }
      else {
        set(modelMode, 'manual');
      }
    }
    catch (error: unknown) {
      logger.error('Failed to load existing oracle price entry:', error);
      notifyError(
        t('event_asset_price_update.fetch_error.title'),
        t('event_asset_price_update.fetch_error.description', { error: getErrorMessage(error) }),
      );
    }
    finally {
      set(loading, false);
    }
  }

  async function save(): Promise<void> {
    const payload = get(modelValue);
    if (!payload)
      return;

    const parsed = get(parsedPrice);
    if (!parsed)
      return;

    const entry = get(existingEntry);
    const nextPrice = get(modelPrice).trim();
    const selectedMode = get(modelMode);
    const unchanged = entry
      && parsed.isEqualTo(entry.price)
      && (selectedMode === 'oracle' || entry.sourceType === PriceOracle.MANUAL);
    if (unchanged) {
      close();
      return;
    }

    set(saving, true);
    try {
      await updatePrice({
        existingEntry: entry,
        fromAsset: payload.asset,
        mode: selectedMode,
        price: nextPrice,
        timestampMs: payload.timestamp,
        toAsset: get(currencySymbol),
      });
      notifyInfo(
        t('event_asset_price_update.success.title'),
        t('event_asset_price_update.success.description'),
      );
      close();
    }
    catch (error: unknown) {
      logger.error('Failed to update event price:', error);
      notifyError(
        t('event_asset_price_update.save_error.title'),
        t('event_asset_price_update.save_error.description', { error: getErrorMessage(error) }),
      );
    }
    finally {
      set(saving, false);
    }
  }

  watch(modelValue, (payload) => {
    if (payload)
      startPromise(load(payload));
  }, { immediate: true });

  return {
    close,
    existingEntry: shallowReadonly(existingEntry),
    existingIsManual,
    loading: readonly(loading),
    modelMode,
    modelPrice,
    open,
    priceErrors,
    priceValid,
    save,
    saving: readonly(saving),
    showModeChoice,
  };
}
