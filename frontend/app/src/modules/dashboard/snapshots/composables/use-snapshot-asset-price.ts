import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { HistoricalPriceFormPayload } from '@/modules/assets/prices/price-types';
import { Zero } from '@rotki/common';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useAssetPricesApi } from '@/modules/assets/api/use-asset-prices-api';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { bigNumberifyFromRef } from '@/modules/core/common/data/bignumbers';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { PriceOracle } from '@/modules/settings/types/price-oracle';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

interface UseSnapshotAssetPriceOptions {
  /** The asset amount (two-way; the form's v-model). */
  amount: Ref<string>;
  /** The stored USD value (two-way; the form's v-model). Always USD. */
  usdValue: Ref<string>;
  /** The asset identifier (two-way; the form's v-model). */
  asset: Ref<string>;
  /** The snapshot timestamp, in SECONDS. */
  timestamp: MaybeRefOrGetter<number>;
}

interface UseSnapshotAssetPriceReturn {
  /** Asset price in USD (bound to the USD-mode primary field). */
  assetToUsdPrice: Ref<string>;
  /** Asset price in the user's display currency (non-USD primary field). */
  assetToFiatPrice: Ref<string>;
  /** Asset value in the user's display currency (non-USD secondary field). */
  fiatValue: Ref<string>;
  /** Whether the user is editing the secondary (value) field. */
  fiatValueFocused: Ref<boolean>;
  /** Whether the user's main currency is USD (no conversion needed). */
  isCurrentCurrencyUsd: ComputedRef<boolean>;
  /** The user's main currency symbol. */
  currencySymbol: Ref<string>;
  /** Whether a historic-price fetch is in flight. */
  fetching: ComputedRef<boolean>;
  /** Persist a user-edited manual price (USD or fiat) for the timestamp. */
  submitPrice: () => Promise<void>;
  /** Clear all derived/fetched price state. */
  reset: () => void;
}

/**
 * Owns the asset <-> USD <-> display-currency price-sync state machine used by
 * the snapshot balance edit form.
 *
 * Snapshots are stored in USD. In a non-USD main currency the user edits the
 * fiat price/value, so the stored `usdValue` must be kept in sync via the
 * historic USD -> fiat rate at the snapshot's timestamp (#12277). That rate is
 * derived from the two fetched asset prices (asset->fiat / asset->USD): it is
 * the rate that applied then and is stable across the user's edits.
 *
 * Extracted from EditBalancesSnapshotAssetPriceForm so this bidirectional,
 * rounding-sensitive logic can be unit-tested without mounting the component.
 */
export function useSnapshotAssetPrice(
  options: UseSnapshotAssetPriceOptions,
): UseSnapshotAssetPriceReturn {
  const { amount, asset, timestamp, usdValue } = options;

  const fiatValue = shallowRef<string>('');
  const assetToUsdPrice = shallowRef<string>('');
  const assetToFiatPrice = shallowRef<string>('');

  const fiatValueFocused = shallowRef<boolean>(false);
  const fetchedAssetToUsdPrice = shallowRef<string>('');
  const fetchedAssetToFiatPrice = shallowRef<string>('');

  const { resetHistoricalPricesData } = useHistoricPriceCache();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { useIsTaskRunning } = useTaskStore();
  const { getHistoricPrice } = usePriceTaskManager();
  const { addHistoricalPrice } = useAssetPricesApi();

  const isCurrentCurrencyUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);
  const fetching = useIsTaskRunning(TaskType.FETCH_HISTORIC_PRICE);

  // The historic USD -> display-currency rate, fetched directly — the SAME rate
  // every snapshot display (SnapshotFiatDisplay) uses to convert the stored USD
  // value back. Driving the fiat->USD storage off this rate (rather than the
  // asset's own USD/fiat price ratio) makes the round-trip exact even for
  // EUR-pegged assets, whose oracle USD price diverges from the forex rate.
  const { rate: usdToFiatRate } = useHistoricFiatConversion(timestamp);

  const numericAssetToUsdPrice = bigNumberifyFromRef(assetToUsdPrice);
  const numericAssetToFiatPrice = bigNumberifyFromRef(assetToFiatPrice);
  const numericFiatValue = bigNumberifyFromRef(fiatValue);
  const numericAmount = bigNumberifyFromRef(amount);
  const numericUsdValue = bigNumberifyFromRef(usdValue);

  async function savePrice(payload: HistoricalPriceFormPayload): Promise<void> {
    await addHistoricalPrice(payload);
    resetHistoricalPricesData([payload]);
  }

  function onAssetToUsdPriceChange(forceUpdate = false): void {
    // USD main currency only: in a non-USD currency the stored USD value is
    // driven from the fiat value via the direct rate (see syncUsdValueFromFiat),
    // so this must not also write it from the asset's USD price.
    if (get(isCurrentCurrencyUsd) && get(amount) && get(assetToUsdPrice) && (!get(fiatValueFocused) || forceUpdate))
      set(usdValue, get(numericAmount).multipliedBy(get(numericAssetToUsdPrice)).toFixed());
  }

  function onAssetToFiatPriceChanged(forceUpdate = false): void {
    if (get(amount) && get(assetToFiatPrice) && (!get(fiatValueFocused) || forceUpdate))
      set(fiatValue, get(numericAmount).multipliedBy(get(numericAssetToFiatPrice)).toFixed());
  }

  function onUsdValueChange(): void {
    if (get(amount) && get(fiatValueFocused))
      set(assetToUsdPrice, get(numericUsdValue).div(get(numericAmount)).toFixed());
  }

  // Keep the stored USD value in sync with the fiat value, using the direct
  // historic USD->fiat rate so it round-trips exactly through the display
  // (#12277). Without this the user's fiat edit is dropped, or (for EUR-pegged
  // assets) stored against the wrong rate.
  function syncUsdValueFromFiat(): void {
    if (get(isCurrentCurrencyUsd) || !get(amount))
      return;

    const rate = get(usdToFiatRate);
    if (rate.isPositive())
      set(usdValue, get(numericFiatValue).div(rate).toFixed());
  }

  function onFiatValueChange(): void {
    if (!get(amount))
      return;

    if (get(fiatValueFocused))
      set(assetToFiatPrice, get(numericFiatValue).div(get(numericAmount)).toFixed());

    syncUsdValueFromFiat();
  }

  async function fetchHistoricPrices(): Promise<void> {
    const assetVal = get(asset);
    const ts = toValue(timestamp);
    if (!ts || !assetVal)
      return;

    // Fallback price (used when a historic lookup is unavailable). Guard the
    // division: an empty/zero amount would otherwise yield NaN/Infinity and
    // poison the price fields.
    const currentAmount = get(numericAmount);
    const oldUsdPrice = currentAmount.isPositive()
      ? get(numericUsdValue).dividedBy(currentAmount)
      : Zero;

    if (assetVal === CURRENCY_USD) {
      set(fetchedAssetToUsdPrice, '1');
    }
    else {
      const price = await getHistoricPrice({ fromAsset: assetVal, timestamp: ts, toAsset: CURRENCY_USD });

      if (price.gt(0))
        set(fetchedAssetToUsdPrice, price.toFixed());
      else
        set(assetToUsdPrice, oldUsdPrice.toFixed());
    }

    if (!get(isCurrentCurrencyUsd)) {
      const currentCurrency = get(currencySymbol);

      if (assetVal === currentCurrency) {
        set(fetchedAssetToFiatPrice, '1');
        return;
      }

      const price = await getHistoricPrice({ fromAsset: assetVal, timestamp: ts, toAsset: currentCurrency });

      if (price.gt(0))
        set(fetchedAssetToFiatPrice, price.toFixed());
      else
        set(assetToFiatPrice, oldUsdPrice.toFixed());
    }
  }

  async function submitPrice(): Promise<void> {
    const assetVal = get(asset);
    if (!assetVal)
      return;

    if (get(isCurrentCurrencyUsd)) {
      if (get(assetToUsdPrice) !== get(fetchedAssetToUsdPrice)) {
        await savePrice({
          fromAsset: assetVal,
          price: get(assetToUsdPrice),
          sourceType: PriceOracle.MANUAL,
          timestamp: toValue(timestamp),
          toAsset: CURRENCY_USD,
        });
      }
    }
    else if (get(assetToFiatPrice) !== get(fetchedAssetToFiatPrice)) {
      await savePrice({
        fromAsset: assetVal,
        price: get(assetToFiatPrice),
        sourceType: PriceOracle.MANUAL,
        timestamp: toValue(timestamp),
        toAsset: get(currencySymbol),
      });
    }
  }

  function reset(): void {
    set(fetchedAssetToUsdPrice, '');
    set(fetchedAssetToFiatPrice, '');
    set(assetToUsdPrice, '');
    set(assetToFiatPrice, '');
    set(fiatValue, '');
    set(usdValue, '');
  }

  // Re-fetch whenever the timestamp or asset changes (fetchHistoricPrices
  // no-ops when there is no asset yet).
  watchImmediate([(): number => toValue(timestamp), asset], async (): Promise<void> => {
    await fetchHistoricPrices();
  });

  watchImmediate(fetchedAssetToUsdPrice, (price) => {
    set(assetToUsdPrice, price);
    onAssetToUsdPriceChange(true);
  });

  watchImmediate(assetToUsdPrice, () => {
    onAssetToUsdPriceChange();
  });

  watchImmediate(usdValue, () => {
    onUsdValueChange();
  });

  watchImmediate(fetchedAssetToFiatPrice, (price) => {
    set(assetToFiatPrice, price);
    onAssetToFiatPriceChanged(true);
  });

  watchImmediate(assetToFiatPrice, () => {
    onAssetToFiatPriceChanged();
  });

  watchImmediate(fiatValue, () => {
    onFiatValueChange();
  });

  watchImmediate(amount, () => {
    if (!get(isCurrentCurrencyUsd)) {
      onAssetToFiatPriceChanged();
      onFiatValueChange();
    }

    onAssetToUsdPriceChange();
    onUsdValueChange();
  });

  // The direct rate resolves asynchronously; re-derive the stored USD value once
  // it is available so a freshly-opened form isn't left with a stale value.
  watch(usdToFiatRate, () => {
    syncUsdValueFromFiat();
  });

  return {
    // These refs are two-way bound (v-model) by the consuming form, so they
    // must stay writable rather than be wrapped in readonly().
    // eslint-disable-next-line @rotki/composable-return-readonly
    assetToFiatPrice,
    // eslint-disable-next-line @rotki/composable-return-readonly
    assetToUsdPrice,
    currencySymbol,
    fetching,
    // eslint-disable-next-line @rotki/composable-return-readonly
    fiatValue,
    // eslint-disable-next-line @rotki/composable-return-readonly
    fiatValueFocused,
    isCurrentCurrencyUsd,
    reset,
    submitPrice,
  };
}
