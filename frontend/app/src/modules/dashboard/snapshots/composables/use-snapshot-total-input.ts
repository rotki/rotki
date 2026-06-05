import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { BalanceSnapshot, LocationDataSnapshot } from '@/modules/dashboard/snapshots';
import { assert, type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { useHistoricFiatConversion } from '@/modules/dashboard/snapshots/composables/use-historic-fiat-conversion';
import { convertFiatToUsd, convertUsdToFiat } from '@/modules/dashboard/snapshots/lib/snapshot-fx';
import {
  assetsTotal,
  getTotalEntry,
  locationsTotal,
  nftsTotal as sumNftsTotal,
} from '@/modules/dashboard/snapshots/lib/snapshot-totals';

export type TotalSuggestionKey = 'asset' | 'location' | 'total';

interface UseSnapshotTotalInputOptions {
  /** The location-data rows (two-way; the total step's v-model). */
  modelValue: Ref<LocationDataSnapshot[]>;
  /** The balance rows the snapshot's total reconciles against. */
  balancesSnapshot: MaybeRefOrGetter<BalanceSnapshot[]>;
  /** The snapshot timestamp, in SECONDS. */
  timestamp: MaybeRefOrGetter<number>;
}

interface UseSnapshotTotalInputReturn {
  /** The total the user enters, in their display currency (the form field). */
  total: Ref<string>;
  /** The stored USD total derived from `total` at the historic rate. */
  numericTotal: ComputedRef<BigNumber>;
  /** Net USD total excluding NFTs (shown in the warning text). */
  nftsExcludedTotal: ComputedRef<BigNumber>;
  /** Calculated totals offered as one-click suggestions. */
  suggestions: ComputedRef<Partial<Record<TotalSuggestionKey, BigNumber>>>;
  /** Whether the historic rate lookup is in flight. */
  fetchingRate: ComputedRef<boolean>;
  /** Whether the rate is usable (USD, or a positive resolved historic rate). */
  rateReady: ComputedRef<boolean>;
  /** Seed the field from a USD value, converting to the display currency. */
  setTotal: (value?: BigNumber) => void;
  /** Persist `numericTotal` into the snapshot's `total` location row. */
  applyTotal: () => void;
}

/**
 * Owns the snapshot total-step input: the user enters the grand total in their
 * display currency, and it is stored in USD using the historic USD -> fiat rate
 * at the snapshot's timestamp (#12277). Also computes the asset/location
 * calculated suggestions. Extracted from EditSnapshotTotal so the rate-gated
 * conversion can be unit-tested without mounting the component.
 */
export function useSnapshotTotalInput(
  options: UseSnapshotTotalInputOptions,
): UseSnapshotTotalInputReturn {
  const { balancesSnapshot, modelValue, timestamp } = options;

  const total = shallowRef<string>('');

  const { isUsd, loading: fetchingRate, rate, rateReady } = useHistoricFiatConversion(timestamp);

  const assetTotal = computed<BigNumber>(() => assetsTotal(toValue(balancesSnapshot)));
  const locationTotal = computed<BigNumber>(() => locationsTotal(get(modelValue)));
  const nftsTotal = computed<BigNumber>(() => sumNftsTotal(toValue(balancesSnapshot)));

  const numericTotal = computed<BigNumber>(() => {
    const value = get(total);

    if (value === '')
      return Zero;

    if (get(isUsd))
      return bigNumberify(value);

    const currentRate = get(rate);
    if (!currentRate.isPositive())
      return Zero;

    return convertFiatToUsd(bigNumberify(value), currentRate);
  });

  const nftsExcludedTotal = computed<BigNumber>(() => get(numericTotal).minus(get(nftsTotal)));

  const suggestions = computed<Partial<Record<TotalSuggestionKey, BigNumber>>>(() => {
    const assetTotalValue = get(assetTotal);
    const locationTotalValue = get(locationTotal);

    if (assetTotalValue.minus(locationTotalValue).abs().lt(1e-8) || !get(isUsd)) {
      return { total: assetTotalValue };
    }
    return { asset: assetTotalValue, location: locationTotalValue };
  });

  function setTotal(value?: BigNumber): void {
    assert(value);
    if (!get(rateReady))
      return;

    set(total, convertUsdToFiat(value, get(rate)).toFixed());
  }

  function applyTotal(): void {
    const newValue = [...get(modelValue)];
    const totalEntry = getTotalEntry(newValue);

    if (totalEntry)
      totalEntry.usdValue = get(numericTotal);

    set(modelValue, newValue);
  }

  // Seed the field from the stored total whenever the rate resolves.
  watchImmediate(rate, (currentRate): void => {
    if (!get(rateReady))
      return;

    const totalEntry = getTotalEntry(get(modelValue));
    if (totalEntry) {
      set(total, get(isUsd)
        ? totalEntry.usdValue.toFixed()
        : convertUsdToFiat(totalEntry.usdValue, currentRate).toFixed());
    }
  });

  return {
    applyTotal,
    fetchingRate,
    nftsExcludedTotal,
    numericTotal,
    rateReady,
    setTotal,
    suggestions,
    // Two-way bound (v-model) by the consuming form, so it stays writable.
    // eslint-disable-next-line @rotki/composable-return-readonly
    total,
  };
}
