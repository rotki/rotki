<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';

const { t } = useI18n({ useScope: 'global' });

const { prices } = storeToRefs(useBalancePricesStore());
const { isAssetIgnored } = useAssetsStore();
const { actionableCount, refreshSummary } = useDataIssuesSummary();
const { fetchUndecodedTransactionsBreakdown, undecodedCount } = useUndecodedTransactionsCount();

// Ignored assets (spam/dust) are hidden from the balances table, so they must
// not inflate the count either — only count assets the user actually sees.
const missingPricesCount = computed<number>(() =>
  Object.entries(get(prices)).filter(([asset, price]) => price.priceMissing && !isAssetIgnored(asset)).length,
);

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
    class="flex flex-wrap items-center gap-2"
    data-testid="dashboard-completeness"
  >
    <RouterLink
      v-if="missingPricesCount > 0"
      class="inline-flex no-underline"
      :to="{ name: '/price-manager/latest/' }"
    >
      <RuiChip
        size="sm"
        color="grey"
        variant="outlined"
        class="cursor-pointer hover:brightness-95"
      >
        <template #prepend>
          <RuiIcon
            name="lu-banknote-x"
            size="14"
          />
        </template>
        {{ t('dashboard.completeness.missing_prices', { count: missingPricesCount }) }}
      </RuiChip>
    </RouterLink>
    <RouterLink
      v-if="undecodedCount > 0"
      class="inline-flex no-underline"
      :to="{ name: '/history/events/' }"
    >
      <RuiChip
        size="sm"
        color="warning"
        variant="outlined"
        class="cursor-pointer hover:brightness-95"
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
      class="inline-flex no-underline"
      :to="{ name: '/history/data-issues/' }"
    >
      <RuiChip
        size="sm"
        color="warning"
        variant="outlined"
        class="cursor-pointer hover:brightness-95"
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
