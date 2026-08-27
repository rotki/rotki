<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/assets/amount-display/types';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';

const { description, tag = 'span', short = false } = defineProps<{
  description: IssueDescription;
  tag?: string;
  short?: boolean;
}>();

// Both keys take the same interpolation slots, so only the sentence length differs.
const keypath = computed<string>(() => short ? description.shortMessageKey : description.messageKey);

const { useAssetField } = useAssetInfoRetrieval();

// Empty until resolved, so the template falls back to the raw `eip155:...` identifier.
const symbol = useAssetField(() => description.asset, 'symbol');
const name = useAssetField(() => description.asset, 'name');

// A native `title` rather than a tooltip component, so a long list of cards stays cheap.
const assetTitle = computed<string>(() => {
  const assetSymbol = get(symbol) || description.asset || '';
  const assetName = get(name);
  const header = assetName && assetName !== assetSymbol ? `${assetSymbol} (${assetName})` : assetSymbol;
  return description.asset && description.asset !== header ? `${header}\n${description.asset}` : header;
});

/**
 * Pins the display precision to the amount's own decimal count.
 *
 * @remarks
 * The default rounding renders a tiny amount as a "less than" threshold, which reads as an
 * approximation in the middle of a sentence that is stating an exact discrepancy.
 */
function exact(amount: BigNumber): FormatOptions {
  return { decimals: amount.decimalPlaces() ?? undefined };
}
</script>

<template>
  <i18n-t
    :keypath="keypath"
    :tag="tag"
    scope="global"
  >
    <template #asset>
      <span
        class="font-medium cursor-help underline decoration-dotted decoration-rui-text-disabled underline-offset-2"
        :title="assetTitle"
      >
        {{ symbol || description.asset }}
      </span>
    </template>
    <template #amount>
      <ValueDisplay
        v-if="description.amounts.amount"
        :value="description.amounts.amount"
        :format="exact(description.amounts.amount)"
        class="font-medium"
      />
    </template>
    <template #before>
      <ValueDisplay
        v-if="description.amounts.before"
        :value="description.amounts.before"
        :format="exact(description.amounts.before)"
        class="font-medium"
      />
    </template>
    <template #derived>
      <ValueDisplay
        v-if="description.amounts.derived"
        :value="description.amounts.derived"
        :format="exact(description.amounts.derived)"
        class="font-medium"
      />
    </template>
    <template #observed>
      <ValueDisplay
        v-if="description.amounts.observed"
        :value="description.amounts.observed"
        :format="exact(description.amounts.observed)"
        class="font-medium"
      />
    </template>
    <template #delta>
      <ValueDisplay
        v-if="description.amounts.delta"
        :value="description.amounts.delta"
        :format="exact(description.amounts.delta)"
        class="font-medium"
      />
    </template>
  </i18n-t>
</template>
