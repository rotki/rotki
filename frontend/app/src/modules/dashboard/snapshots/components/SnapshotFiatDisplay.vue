<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';

defineOptions({
  inheritAttrs: false,
});

/**
 * Displays a USD-denominated snapshot value in the user's currency, converted at the *historic* rate
 * of the snapshot's timestamp.
 *
 * @remarks
 * Every value stored in a snapshot is USD, so showing it in another main currency needs the rate that
 * applied at the snapshot's time. Prefer this over `FiatDisplay from="USD"` throughout the snapshot
 * editor: it is the spelling that cannot get either foot-gun wrong.
 *
 * Omitting the timestamp silently falls back to today's rate, which looks correct on screen.
 *
 * The snapshot `timestamp` is in **seconds**. `normalizeTimestamp` reads a bare number as seconds
 * but `{ ms }` as milliseconds, so `{ ms: timestamp }` floors to a near-zero key, finds no historic
 * price, and renders 0.
 */
const { value, timestamp } = defineProps<{
  /** The value to display, denominated in USD. */
  value: BigNumber;
  /** The snapshot timestamp, in seconds (used for the historic FX lookup). */
  timestamp: number;
}>();
</script>

<template>
  <FiatDisplay
    :value="value"
    from="USD"
    :timestamp="timestamp"
    v-bind="$attrs"
  />
</template>
