<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';

const { t } = useI18n({ useScope: 'global' });

const { prices } = storeToRefs(useBalancePricesStore());
const { decodingStatus } = storeToRefs(useDecodingStatusStore());
const { actionableCount, refreshSummary } = useDataIssuesSummary();
const { fetchUndecodedTransactionsBreakdown } = useHistoryTransactionDecoding();
const { processing } = useHistoryEventsStatus();

const missingPricesCount = computed<number>(() =>
  Object.values(get(prices)).filter(price => price.priceMissing).length,
);

const undecodedCount = computed<number>(() => {
  if (get(processing))
    return 0;
  return get(decodingStatus).reduce((sum, { processed, total }) => sum + Math.max(0, total - processed), 0);
});

const hasIssues = computed<boolean>(() =>
  get(missingPricesCount) > 0 || get(undecodedCount) > 0 || get(actionableCount) > 0,
);

onMounted(() => {
  startPromise(Promise.all([fetchUndecodedTransactionsBreakdown(), refreshSummary()]));
});
</script>

<template>
  <div
    v-if="hasIssues"
    class="flex flex-wrap gap-2 mt-2"
    data-cy="dashboard-completeness"
  >
    <RouterLink
      v-if="missingPricesCount > 0"
      :to="{ name: '/price-manager/latest/' }"
    >
      <RuiChip
        size="sm"
        color="warning"
        clickable
      >
        <template #prepend>
          <RuiIcon
            name="lu-circle-help"
            size="14"
          />
        </template>
        {{ t('dashboard.completeness.missing_prices', { count: missingPricesCount }) }}
      </RuiChip>
    </RouterLink>
    <RouterLink
      v-if="undecodedCount > 0"
      :to="{ name: '/history/events/' }"
    >
      <RuiChip
        size="sm"
        color="warning"
        clickable
      >
        <template #prepend>
          <RuiIcon
            name="lu-triangle-alert"
            size="14"
          />
        </template>
        {{ t('dashboard.completeness.undecoded', { count: undecodedCount }) }}
      </RuiChip>
    </RouterLink>
    <RouterLink
      v-if="actionableCount > 0"
      :to="{ name: '/history/data-issues/' }"
    >
      <RuiChip
        size="sm"
        color="warning"
        clickable
      >
        <template #prepend>
          <RuiIcon
            name="lu-inbox"
            size="14"
          />
        </template>
        {{ t('dashboard.completeness.data_issues', { count: actionableCount }) }}
      </RuiChip>
    </RouterLink>
  </div>
</template>
