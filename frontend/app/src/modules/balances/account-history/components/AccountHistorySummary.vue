<script setup lang="ts">
import type { BalanceSummary } from '@/modules/balances/account-history/balance-series';
import { RuiChip, RuiProgress } from '@rotki/ui-library';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { AssetAmountDisplay } from '@/modules/assets/amount-display/components';

const { asset, processingRequired = false, summary } = defineProps<{
  /** Absent while there is no balance to show; the amounts then read as dashes, keeping the row's place. */
  asset?: string;
  summary: BalanceSummary;
  /** The backend has events in the range it has not replayed yet, so these balances may be behind. */
  processingRequired?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const changeColor = computed<string>(() => {
  if (summary.change.isPositive() && !summary.change.isZero())
    return 'text-rui-success';
  if (summary.change.isNegative())
    return 'text-rui-error';
  return '';
});
</script>

<template>
  <div class="flex flex-wrap items-end justify-between gap-4">
    <div class="flex flex-wrap gap-8">
      <div data-testid="account-history-current">
        <div class="text-sm text-rui-text-secondary">
          {{ t('account_history.summary.current') }}
        </div>
        <AssetAmountDisplay
          v-if="asset"
          class="text-h5 font-medium"
          :amount="summary.current"
          :asset="asset"
        />
        <div
          v-else
          class="text-h5 font-medium text-rui-text-secondary"
        >
          -
        </div>
      </div>
      <div data-testid="account-history-change">
        <div class="text-sm text-rui-text-secondary">
          {{ t('account_history.summary.change') }}
        </div>
        <AssetAmountDisplay
          v-if="asset"
          class="text-h5 font-medium"
          :class="changeColor"
          :amount="summary.change"
          :asset="asset"
        />
        <div
          v-else
          class="text-h5 font-medium text-rui-text-secondary"
        >
          -
        </div>
      </div>
    </div>
    <RuiChip
      v-if="processingRequired"
      size="sm"
      color="warning"
      data-testid="account-history-processing"
    >
      <div class="flex items-center gap-1.5">
        <RuiProgress
          variant="indeterminate"
          circular
          size="12"
          thickness="2"
          color="warning"
        />
        {{ t('account_history.processing') }}
      </div>
    </RuiChip>
  </div>
</template>
