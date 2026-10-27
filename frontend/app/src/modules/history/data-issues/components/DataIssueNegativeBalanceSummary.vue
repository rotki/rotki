<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import DataIssueValueTile from '@/modules/history/data-issues/components/DataIssueValueTile.vue';

/** A negative balance laid out as the balance before and after the event that took it below zero. */
const { before, after, untrackedExchange, asset } = defineProps<{
  before: BigNumber;
  after: BigNumber;
  untrackedExchange: boolean;
  asset?: string;
}>();

const { t } = useI18n({ useScope: 'global' });
const { useAssetField } = useAssetInfoRetrieval();
const symbol = useAssetField(() => asset, 'symbol');

/** Each value at its own precision, so a tiny shortfall is not rounded to zero; an exact zero keeps the user's. */
function decimalsOf(amount: BigNumber): number | undefined {
  return amount.isZero() ? undefined : amount.decimalPlaces() ?? undefined;
}
</script>

<template>
  <div
    class="@container flex flex-col gap-2 text-sm"
    data-testid="data-issue-negative-summary"
  >
    <div class="grid grid-cols-1 gap-2 @sm:grid-cols-2">
      <DataIssueValueTile :label="t('data_issues.detail.before_event')">
        <AssetAmountDisplay
          :amount="before"
          :asset="asset"
          :decimals="decimalsOf(before)"
          no-collection-parent
          data-testid="data-issue-negative-before"
        />
      </DataIssueValueTile>
      <DataIssueValueTile
        :label="t('data_issues.detail.after_event')"
        warning
      >
        <AssetAmountDisplay
          class="font-medium text-rui-warning"
          :amount="after"
          :asset="asset"
          :decimals="decimalsOf(after)"
          no-collection-parent
          data-testid="data-issue-negative-after"
        />
      </DataIssueValueTile>
    </div>
    <p
      v-if="untrackedExchange"
      class="text-xs text-rui-text-secondary"
      data-testid="data-issue-negative-cause"
    >
      {{ t('data_issues.detail.untracked_exchange_cause') }}
    </p>
    <p
      v-else-if="symbol || asset"
      class="text-xs text-rui-text-secondary"
      data-testid="data-issue-negative-cause"
    >
      {{ t('data_issues.detail.negative_balance_cause', { asset: symbol || asset }) }}
    </p>
  </div>
</template>
