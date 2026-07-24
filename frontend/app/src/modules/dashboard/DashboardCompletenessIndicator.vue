<script setup lang="ts">
import { startPromise } from '@shared/utils';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { useUndecodedTransactionsCount } from '@/modules/history/events/tx/use-undecoded-transactions-count';
import DashboardMissingPricesDialog from './DashboardMissingPricesDialog.vue';
import { useMissingPrices } from './use-missing-prices';

const { t } = useI18n({ useScope: 'global' });

const missingPricesDialog = ref<boolean>(false);

const { missingPriceIdentifiers, missingPricesCount } = useMissingPrices();
const { actionableCount, refreshSummary } = useDataIssuesSummary();
const { fetchUndecodedTransactionsBreakdown, undecodedCount } = useUndecodedTransactionsCount();

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
    <RuiButton
      v-if="missingPricesCount > 0"
      size="sm"
      color="secondary"
      variant="outlined"
      data-testid="missing-prices-trigger"
      @click="missingPricesDialog = true"
    >
      <template #prepend>
        <RuiIcon
          name="lu-banknote-x"
          size="14"
        />
      </template>
      {{ t('dashboard.completeness.missing_prices', { count: missingPricesCount }, missingPricesCount) }}
    </RuiButton>
    <RouterLink
      v-if="undecodedCount > 0"
      class="no-underline"
      :to="{ name: '/history/events/' }"
    >
      <RuiButton
        size="sm"
        color="warning"
        variant="outlined"
      >
        <template #prepend>
          <RuiIcon
            name="lu-triangle-alert"
            size="14"
          />
        </template>
        {{ t('dashboard.completeness.undecoded', { count: undecodedCount }, undecodedCount) }}
      </RuiButton>
    </RouterLink>
    <RouterLink
      v-if="actionableCount > 0"
      class="no-underline"
      :to="{ name: '/history/data-issues/' }"
    >
      <RuiButton
        size="sm"
        color="warning"
        variant="outlined"
      >
        <template #prepend>
          <RuiIcon
            name="lu-inbox"
            size="14"
          />
        </template>
        {{ t('dashboard.completeness.data_issues', { count: actionableCount }, actionableCount) }}
      </RuiButton>
    </RouterLink>
  </div>

  <DashboardMissingPricesDialog
    v-model:open="missingPricesDialog"
    :identifiers="missingPriceIdentifiers"
  />
</template>
