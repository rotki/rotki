<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import type { FormatOptions } from '@/modules/assets/amount-display/types';
import type { IssueDescription } from '@/modules/history/data-issues/types';
import { ValueDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';

const { description, tag = 'span' } = defineProps<{
  description: IssueDescription;
  tag?: string;
}>();

const { useAssetField } = useAssetInfoRetrieval();

// Resolve the asset identifier to its symbol so the sentence reads with a short
// symbol (e.g. "USDC") instead of the raw `eip155:...` identifier. Falls back to
// the identifier only when the asset cannot be resolved at all.
const symbol = useAssetField(() => description.asset, 'symbol');
const name = useAssetField(() => description.asset, 'name');

// The sentence shows the symbol only; the hover title carries the fuller identity:
// "Symbol (Name)" then the raw identifier on the next line. Native title so it stays
// zero-cost across a list of cards.
const assetTitle = computed<string>(() => {
  const assetSymbol = get(symbol) || description.asset || '';
  const assetName = get(name);
  const header = assetName && assetName !== assetSymbol ? `${assetSymbol} (${assetName})` : assetSymbol;
  return description.asset && description.asset !== header ? `${header}\n${description.asset}` : header;
});

// Render the exact amount (its own decimal count) so tiny values show in full
// rather than the rounded "< 0.001" form, which reads awkwardly in the sentence.
function exact(amount: BigNumber): FormatOptions {
  return { decimals: amount.decimalPlaces() ?? undefined };
}
</script>

<template>
  <i18n-t
    :keypath="description.messageKey"
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
