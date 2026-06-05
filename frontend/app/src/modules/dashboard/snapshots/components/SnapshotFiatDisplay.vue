<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';

defineOptions({
  inheritAttrs: false,
});

/**
 * Displays a USD-denominated snapshot value in the user's currency, converted
 * at the *historic* rate of the snapshot's timestamp.
 *
 * Why this wrapper exists
 * -----------------------
 * Every value stored in a snapshot is USD. Showing it in a non-USD main
 * currency must use the FX rate that applied *at the snapshot's time*, not
 * today's rate (#12277). With `FiatDisplay` that means always pairing
 * `from="USD"` with the snapshot timestamp.
 *
 * Two foot-guns made this worth centralising:
 *  - Forgetting the timestamp entirely falls back to today's FX rate — a silent
 *    correctness bug that looks fine on screen.
 *  - The snapshot `timestamp` is in **seconds**. `FiatDisplay`/`normalizeTimestamp`
 *    treat a raw number as seconds but `{ ms }` as milliseconds, so passing
 *    `{ ms: timestamp }` floors it to a near-zero key, the historic price is
 *    never found, and the value renders as 0.
 *
 * This component is the single correct spelling: pass a USD `value` and the
 * snapshot `timestamp` (seconds), and historic conversion is guaranteed. Prefer
 * it over `FiatDisplay from="USD"` anywhere in the snapshot editor.
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
