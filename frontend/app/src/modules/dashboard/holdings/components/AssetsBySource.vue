<script setup lang="ts">
import type { LegendJump, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { useTrackedAccountsRow } from '@/modules/accounts/use-tracked-accounts-row';
import ActionEmptyState from '@/modules/core/action-center/ActionEmptyState.vue';
import SourceBar from '@/modules/dashboard/holdings/components/SourceBar.vue';
import SourceLegend from '@/modules/dashboard/holdings/components/SourceLegend.vue';
import { useDashboardHoldings } from '@/modules/dashboard/holdings/use-dashboard-holdings';
import { useSourceKindLabel } from '@/modules/dashboard/holdings/use-source-kind-label';
import { useNetWorthLoading } from '@/modules/dashboard/use-net-worth-loading';
import { useSetting } from '@/modules/settings/use-setting';

const selectedKind = defineModel<SourceKind | undefined>('selectedKind');

/** The element ids of the tables a legend row scrolls to. */
const JUMP_TARGETS: Record<LegendJump, string> = {
  liabilities: 'dashboard-liabilities',
  nft: 'nft-balance-table-section',
};

const { t } = useI18n({ useScope: 'global' });

const { summary } = useDashboardHoldings();
const isInitialLoading = useNetWorthLoading();
const shouldShowPercentage = useSetting('shouldShowPercentage');
const kindLabel = useSourceKindLabel();

/**
 * Nothing added at all, which the action center's row says and offers the fix for.
 *
 * @remarks
 * Read from what is added, not from what it holds: a source added with nothing in it (an empty
 * address, a connected exchange at zero) needs the legend's add row, not a prompt to get started.
 */
const { raised: isEmpty, row: trackedAccountsRow } = useTrackedAccountsRow();

const barLabel = computed<string>(() => {
  const parts = get(summary).sources.map(source => `${kindLabel(source.kind)} ${source.share.multipliedBy(100).toFixed(1)}%`);
  return t('dashboard.holdings.legend_label', { parts: parts.join(', ') });
});

function jump(target: LegendJump): void {
  document.getElementById(JUMP_TARGETS[target])?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
</script>

<template>
  <div
    class="grid gap-2"
    data-testid="dashboard-assets-by-source"
  >
    <div class="flex justify-between text-xs text-rui-text-secondary">
      <span>{{ t('dashboard.holdings.title') }}</span>
      <span v-if="shouldShowPercentage && !isEmpty">{{ t('dashboard.holdings.share_of_assets') }}</span>
    </div>
    <div
      v-if="isEmpty"
      class="rounded-md border border-dashed border-rui-grey-300 dark:border-rui-grey-700 p-4"
      data-testid="dashboard-holdings-empty"
    >
      <ActionEmptyState :item="trackedAccountsRow" />
    </div>
    <SourceBar
      v-else-if="!isInitialLoading && !summary.loading && summary.sources.length > 0"
      :sources="summary.sources"
      :show-shares="shouldShowPercentage"
      :selected-kind="selectedKind"
      :label="shouldShowPercentage ? barLabel : t('dashboard.holdings.title')"
    />
    <RuiSkeletonLoader
      v-else-if="isInitialLoading || summary.loading"
      class="h-2.5"
      data-testid="dashboard-source-bar-loading"
    />
    <SourceLegend
      v-if="!isEmpty"
      :summary="summary"
      :selected-kind="selectedKind"
      :loading="isInitialLoading"
      @select="selectedKind = $event"
      @jump="jump($event)"
    />
  </div>
</template>
