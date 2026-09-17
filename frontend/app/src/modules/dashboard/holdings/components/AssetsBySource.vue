<script setup lang="ts">
import type { LegendJump, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
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
      <span v-if="shouldShowPercentage">{{ t('dashboard.holdings.share_of_assets') }}</span>
    </div>
    <SourceBar
      v-if="!isInitialLoading && !summary.loading && summary.sources.length > 0"
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
      :summary="summary"
      :selected-kind="selectedKind"
      :loading="isInitialLoading"
      @select="selectedKind = $event"
      @jump="jump($event)"
    />
  </div>
</template>
