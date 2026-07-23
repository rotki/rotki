<script setup lang="ts">
import { type BigNumber, Zero } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * Displays the change in net worth versus the chronologically previous snapshot,
 * in the user's display currency, at each side's own *historic* rate (#12277).
 *
 * The conversion is done here (not in `useSnapshotList`) so it only runs for the
 * rows the table actually renders — the visible page. Eagerly converting the
 * whole series was what hammered the forex endpoint. Each mounted cell resolves
 * at most two historic rates (its own + its predecessor's) through the shared,
 * debounced, LRU-backed cache, so the working set stays ~page-size.
 */
const { previousTimestamp, previousUsdValue, timestamp, value } = defineProps<{
  /** This snapshot's net worth, denominated in USD. */
  value: BigNumber;
  /** This snapshot's timestamp, in seconds (historic FX lookup). */
  timestamp: number;
  /** The previous snapshot's net worth (USD); absent for the oldest snapshot. */
  previousUsdValue?: BigNumber;
  /** The previous snapshot's timestamp (seconds); absent for the oldest. */
  previousTimestamp?: number;
}>();

const { createKey, getHistoricPrice, getIsPending } = useHistoricPriceCache();
const currencySymbol = useSetting('currencySymbol');

const isUsd = computed<boolean>(() => get(currencySymbol) === CURRENCY_USD);

interface Converted {
  fiatValue: BigNumber;
  pending: boolean;
  ready: boolean;
}

/** Converts a USD net worth to display currency at its historic rate (lazy). */
function convert(ts: number, usdValue: BigNumber): Converted {
  if (get(isUsd))
    return { fiatValue: usdValue, pending: false, ready: true };

  const rate = getHistoricPrice(CURRENCY_USD, ts);
  const pending = getIsPending(createKey(CURRENCY_USD, ts));
  const ready = rate.isPositive();
  return { fiatValue: ready ? usdValue.multipliedBy(rate) : Zero, pending, ready };
}

const current = computed<Converted>(() => convert(timestamp, value));

const previous = computed<Converted | undefined>(() => {
  if (previousTimestamp === undefined || previousUsdValue === undefined)
    return undefined;
  return convert(previousTimestamp, previousUsdValue);
});

/** True while either side's historic rate is still loading. */
const pending = computed<boolean>(() => get(current).pending || (get(previous)?.pending ?? false));

/**
 * The Δ, or `undefined` when it cannot be shown: the oldest snapshot has no
 * predecessor, and a not-yet-ready (loading or permanently missing) rate on
 * either side must not produce a bogus zero-based delta.
 */
const delta = computed<BigNumber | undefined>(() => {
  const prev = get(previous);
  const cur = get(current);
  if (!prev || !cur.ready || !prev.ready)
    return undefined;
  return cur.fiatValue.minus(prev.fiatValue);
});

/** Placeholder for "no change to show" (avoids a raw i18n text node). */
const placeholder = '—';
</script>

<template>
  <RuiSkeletonLoader
    v-if="pending"
    class="w-20 ml-auto"
  />
  <FiatDisplay
    v-else-if="delta"
    :value="delta"
    pnl
  />
  <span v-else>{{ placeholder }}</span>
</template>
