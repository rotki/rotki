import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

interface UseSnapshotFxOverrideReturn {
  /** Whether the display currency is USD (no FX needed; the control hides). */
  isUsd: ComputedRef<boolean>;
  /** The resolved USD -> display-currency rate at the snapshot's timestamp. */
  rate: ComputedRef<BigNumber>;
  /** Whether `rate` is usable (USD, or a positive resolved historic rate). */
  rateReady: ComputedRef<boolean>;
  /** Whether the historic-rate lookup is in flight. */
  loading: ComputedRef<boolean>;
  /** The user's display currency symbol (the override's target asset). */
  currencySymbol: ComputedRef<string>;
  /** Whether an override write (add/edit/delete) is in flight. */
  saving: Readonly<Ref<boolean>>;
  /** The manual override rate stored at this timestamp, if any. */
  currentOverride: ComputedRef<BigNumber | undefined>;
  /** Re-reads whether a manual override exists at this timestamp. */
  refreshOverride: () => Promise<void>;
  /** Stores (or replaces) the manual USD -> currency rate and busts the cache. */
  setOverride: (value: BigNumber) => Promise<boolean>;
  /** Removes the manual rate at this timestamp and busts the cache. */
  clearOverride: () => Promise<boolean>;
}

/**
 * Lets the snapshot editor set a manual historic USD -> display-currency rate
 * for a snapshot whose forex rate the backend can't resolve (#12277 dead-end:
 * value inputs disable when no rate exists). Writes a MANUAL historical price
 * at the snapshot's exact timestamp, then resets the historic-price cache for
 * that asset within ±1h so the editor immediately re-reads the new rate.
 *
 * Because the cache reset spans ±1h (see `resetHistoricalPricesData`), a manual
 * override also affects any other historic lookup of that currency within an
 * hour of the snapshot — the control surfaces this caveat to the user.
 *
 * @param timestamp the snapshot timestamp in SECONDS (value, ref or getter).
 */
export function useSnapshotFxOverride(timestamp: MaybeRefOrGetter<number>): UseSnapshotFxOverrideReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { isUsd, loading, rate, rateReady } = useHistoricFiatConversion(timestamp);
  const { addHistoricalPrice, deleteHistoricalPrice, editHistoricalPrice, fetchHistoricalPrices } = useAssetPricesApi();
  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { notifyError } = useNotifications();

  const saving = shallowRef<boolean>(false);
  const override = shallowRef<BigNumber>();
  const currentOverride = computed<BigNumber | undefined>(() => get(override));

  function basePayload(): Omit<HistoricalPriceFormPayload, 'price'> {
    return {
      fromAsset: CURRENCY_USD,
      sourceType: PriceOracle.MANUAL,
      timestamp: toValue(timestamp),
      toAsset: get(currencySymbol),
    };
  }

  async function refreshOverride(): Promise<void> {
    if (get(isUsd)) {
      set(override, undefined);
      return;
    }
    try {
      const prices = await fetchHistoricalPrices({ fromAsset: CURRENCY_USD, toAsset: get(currencySymbol) });
      const ts = toValue(timestamp);
      set(override, prices.find(price => price.timestamp === ts)?.price);
    }
    catch {
      set(override, undefined);
    }
  }

  async function persist(write: () => Promise<boolean>): Promise<boolean> {
    set(saving, true);
    try {
      const success = await write();
      if (success) {
        // Busts the cached rate for this currency within ±1h so the editor
        // re-reads the new value on next access.
        resetHistoricalPricesData([{ fromAsset: CURRENCY_USD, timestamp: toValue(timestamp) }]);
        await refreshOverride();
      }
      return success;
    }
    catch (error: unknown) {
      notifyError(t('dashboard.snapshot.detail.fx_override.error.title'), getErrorMessage(error));
      return false;
    }
    finally {
      set(saving, false);
    }
  }

  async function setOverride(value: BigNumber): Promise<boolean> {
    const payload: HistoricalPriceFormPayload = { ...basePayload(), price: value.toFixed() };
    const update = get(currentOverride) !== undefined;
    return persist(async () => (update ? editHistoricalPrice(payload) : addHistoricalPrice(payload)));
  }

  async function clearOverride(): Promise<boolean> {
    if (get(currentOverride) === undefined)
      return false;
    return persist(async () => deleteHistoricalPrice(basePayload()));
  }

  return {
    clearOverride,
    currencySymbol,
    currentOverride,
    isUsd,
    loading,
    rate,
    rateReady,
    refreshOverride,
    saving: readonly(saving),
    setOverride,
  };
}
