<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { startPromise } from '@shared/utils';
import { useDataIssuesAutoReload } from '@/modules/history/data-issues/use-data-issues-auto-reload';
import { useDataIssuesSummary } from '@/modules/history/data-issues/use-data-issues-summary';
import { useBucketReconciliation } from '@/modules/history/reconciliation/use-bucket-reconciliation';

const { t } = useI18n({ useScope: 'global' });
const currentRoute = useRouter().currentRoute;

const { actionableCount, refreshSummary: refreshIssuesSummary } = useDataIssuesSummary();
const { attention, refreshSummary, summaryFailed, summaryUnavailable, totals } = useBucketReconciliation();

/**
 * The badge counts the work waiting on each tab: open/unresolved issues on the left, mismatch and
 * blocked balances on the right. The two numbers count different things and are not expected to
 * match.
 */
const reconciliationCount = computed<number>(() =>
  (get(summaryFailed) || get(summaryUnavailable) ? 0 : get(attention)));

/** Red while a balance mismatches, amber when only stopped processing is waiting. */
const reconciliationBadgeClass = computed<string>(() => (get(totals).mismatch > 0
  ? 'bg-rui-error/10 text-rui-error'
  : 'bg-rui-warning/10 text-rui-warning'));

function tabLink(tab: 'issues' | 'reconciliation'): RouteLocationRaw {
  return {
    name: '/history/data-issues/[[tab]]',
    params: { tab },
    query: { keepScrollPosition: 'true' },
  };
}

async function refreshInactiveTab(): Promise<void> {
  const { params } = get(currentRoute);
  if ('tab' in params && params.tab === 'reconciliation')
    await refreshIssuesSummary();
  else
    await refreshSummary();
}

useDataIssuesAutoReload(refreshInactiveTab);

onMounted(() => {
  startPromise(refreshInactiveTab());
});
</script>

<template>
  <RuiTabs
    color="primary"
    variant="segmented"
    data-testid="data-issues-tabs"
  >
    <RuiTab
      link
      :to="tabLink('issues')"
    >
      <span class="flex items-center gap-1.5">
        {{ t('data_issues.tabs.issues') }}
        <span
          v-if="actionableCount > 0"
          class="rounded-full bg-rui-error/10 px-1.5 text-xs font-medium text-rui-error tabular-nums"
          data-testid="data-issues-tab-issues-count"
        >
          {{ actionableCount }}
        </span>
      </span>
    </RuiTab>
    <RuiTab
      link
      :to="tabLink('reconciliation')"
    >
      <span class="flex items-center gap-1.5">
        {{ t('data_issues.tabs.reconciliation') }}
        <span
          v-if="reconciliationCount > 0"
          class="rounded-full px-1.5 text-xs font-medium tabular-nums"
          :class="reconciliationBadgeClass"
          data-testid="data-issues-tab-reconciliation-count"
        >
          {{ reconciliationCount }}
        </span>
      </span>
    </RuiTab>
  </RuiTabs>
</template>
