<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { sharedDecimals } from '@/modules/assets/amount-display/amount-comparison';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import AmountDiffDisplay from '@/modules/assets/amount-display/components/AmountDiffDisplay.vue';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import DataIssueValueTile from '@/modules/history/data-issues/components/DataIssueValueTile.vue';

/** A balance mismatch laid out as values, so the two balances can be compared without reading a sentence. */
const { derived, observed, delta, asset } = defineProps<{
  derived: BigNumber;
  observed: BigNumber;
  delta: BigNumber;
  asset?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { useAssetField } = useAssetInfoRetrieval();
const symbol = useAssetField(() => asset, 'symbol');

/** One precision for both balances, so they line up and the split lands on the first real difference. */
const decimals = computed<number>(() => sharedDecimals(derived, observed));
</script>

<template>
  <div
    class="@container flex flex-col gap-2 text-sm"
    data-testid="data-issue-mismatch-summary"
  >
    <div class="grid grid-cols-1 gap-2 @sm:grid-cols-2 @[40rem]:grid-cols-3">
      <DataIssueValueTile :label="t('balance_divergence.tracked')">
        <AmountDiffDisplay
          :amount="derived"
          :reference="observed"
          :decimals="decimals"
          data-testid="data-issue-mismatch-tracked"
        />
      </DataIssueValueTile>
      <DataIssueValueTile :label="t('balance_divergence.onchain')">
        <AmountDiffDisplay
          :amount="observed"
          :reference="derived"
          :decimals="decimals"
          data-testid="data-issue-mismatch-onchain"
        />
      </DataIssueValueTile>
      <DataIssueValueTile
        :label="t('balance_divergence.difference')"
        warning
        class="@sm:col-span-2 @[40rem]:col-span-1"
      >
        <AssetAmountDisplay
          class="font-medium text-rui-warning"
          :amount="delta"
          :asset="asset"
          :decimals="delta.decimalPlaces() ?? undefined"
          no-collection-parent
          data-testid="data-issue-mismatch-delta"
        />
      </DataIssueValueTile>
    </div>
    <p
      v-if="symbol || asset"
      class="text-xs text-rui-text-secondary"
      data-testid="data-issue-mismatch-cause"
    >
      {{ t('data_issues.detail.mismatch_cause', { asset: symbol || asset }) }}
    </p>
  </div>
</template>
