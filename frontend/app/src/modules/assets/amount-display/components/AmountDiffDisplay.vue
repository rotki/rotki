<script setup lang="ts">
/**
 * Displays an amount with the digits it does not share with a reference amount emphasised, so two
 * long values can be compared at a glance. Values of different magnitude, or that already differ at
 * their first significant digit, render plainly: their digits do not line up, or the emphasis would
 * cover the whole number.
 *
 * @remarks
 * Both values are scrambled and formatted with the same options before they are compared, so the
 * split follows the user's separators and never reveals a real digit in privacy mode; copying takes
 * the scrambled value too, as `AmountDisplayBase` does. Pin
 * `decimals` to keep the two strings aligned: without it the formatter may round or abbreviate
 * each value differently.
 */
import type { BigNumber } from '@rotki/common';
import { useAmountDisplaySettings, useAmountFormatter, useScrambledValue } from '@/modules/assets/amount-display';
import { sameMagnitude, sharesSignificantDigit, splitSharedPrefix } from '@/modules/assets/amount-display/amount-comparison';
import CopyTooltip from '@/modules/shell/components/CopyTooltip.vue';

const { amount, reference, decimals } = defineProps<{
  amount: BigNumber;
  reference: BigNumber;
  decimals?: number;
}>();

const { shouldShowAmount } = useAmountDisplaySettings();
const { scrambledValue } = useScrambledValue({ value: () => amount });
const { scrambledValue: scrambledReference } = useScrambledValue({ value: () => reference });
const { renderedValue, tooltip } = useAmountFormatter({ decimals: () => decimals, rounding: 'amount', value: scrambledValue });
const { renderedValue: renderedReference } = useAmountFormatter({ decimals: () => decimals, rounding: 'amount', value: scrambledReference });

const parts = computed<ReturnType<typeof splitSharedPrefix>>(() => splitSharedPrefix(get(renderedValue), get(renderedReference)));
const emphasise = computed<boolean>(() => !!get(parts).rest
  && sameMagnitude(get(scrambledValue), get(scrambledReference))
  && sharesSignificantDigit(get(parts)));
</script>

<template>
  <span
    class="inline-flex max-w-full"
    :class="{ blur: !shouldShowAmount }"
    data-testid="amount-diff-display"
  >
    <CopyTooltip
      :disabled="!shouldShowAmount"
      :tooltip="tooltip"
      :value="scrambledValue.toFixed()"
    >
      <template v-if="emphasise">
        <span
          class="text-rui-text-secondary"
          data-testid="amount-diff-shared"
          v-text="parts.shared"
        /><span
          class="font-medium text-rui-warning"
          data-testid="amount-diff-rest"
          v-text="parts.rest"
        />
      </template>
      <span
        v-else
        v-text="parts.shared + parts.rest"
      />
    </CopyTooltip>
  </span>
</template>
