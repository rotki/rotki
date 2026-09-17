<script setup lang="ts">
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import AddSourceMenu from '@/modules/dashboard/holdings/components/AddSourceMenu.vue';
import {
  ExtraKind,
  type HoldingsSummary,
  type LegendJump,
  type SourceKind,
  type SourceTotal,
} from '@/modules/dashboard/holdings/core/holdings-types';
import { SOURCE_KIND_COLOR } from '@/modules/dashboard/holdings/source-kind-style';
import { useSourceKindLabel } from '@/modules/dashboard/holdings/use-source-kind-label';
import PercentageDisplay from '@/modules/shell/components/display/PercentageDisplay.vue';

const { loading = false, selectedKind, summary } = defineProps<{
  summary: HoldingsSummary;
  selectedKind?: SourceKind;
  loading?: boolean;
}>();

const emit = defineEmits<{
  select: [kind: SourceKind | undefined];
  jump: [target: LegendJump];
}>();

const { t } = useI18n({ useScope: 'global' });

const kindLabel = useSourceKindLabel();

const LOADING_ROWS = 4;

function sharePercent(source: SourceTotal): string {
  return source.share.multipliedBy(100).toFixed(2);
}

function choose(source: SourceTotal): void {
  if (source.kind === ExtraKind.NFT)
    emit('jump', 'nft');
  else
    emit('select', selectedKind === source.kind ? undefined : source.kind);
}
</script>

<template>
  <ul
    class="grid"
    data-testid="dashboard-source-legend"
  >
    <template v-if="loading">
      <li
        v-for="row in LOADING_ROWS"
        :key="row"
        class="py-1"
      >
        <RuiSkeletonLoader class="h-5" />
      </li>
    </template>
    <template v-else>
      <li
        v-for="source in summary.sources"
        :key="source.kind"
      >
        <button
          type="button"
          class="grid grid-cols-[10px_1fr_auto_4.5rem] items-center gap-2.5 w-full px-1.5 py-1 rounded text-left text-sm hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800"
          :class="{ '!bg-rui-primary/10': selectedKind === source.kind }"
          :aria-pressed="source.kind === ExtraKind.NFT ? undefined : selectedKind === source.kind"
          :data-kind="source.kind"
          data-testid="dashboard-source-legend-row"
          @click="choose(source)"
        >
          <span
            class="size-2.5 rounded-sm"
            :class="SOURCE_KIND_COLOR[source.kind]"
          />
          <span class="flex items-center gap-1 truncate">
            {{ kindLabel(source.kind) }}
            <RuiIcon
              v-if="source.kind === ExtraKind.NFT"
              name="lu-arrow-down"
              size="14"
              class="text-rui-text-secondary"
            />
          </span>
          <template v-if="source.loading">
            <RuiSkeletonLoader
              class="h-4 w-20 justify-self-end"
              data-testid="dashboard-source-legend-row-loading"
            />
            <RuiSkeletonLoader class="h-3 w-10 justify-self-end" />
          </template>
          <template v-else>
            <FiatDisplay
              class="text-right"
              :value="source.value"
            />
            <PercentageDisplay
              class="text-rui-text-secondary text-xs"
              justify="end"
              :value="sharePercent(source)"
            />
          </template>
        </button>
      </li>
      <li
        v-if="!summary.liabilities.isZero()"
        class="border-t border-default mt-1 pt-1"
      >
        <button
          type="button"
          class="grid grid-cols-[10px_1fr_auto_4.5rem] items-center gap-2.5 w-full px-1.5 py-1 rounded text-left text-sm hover:bg-rui-grey-100 dark:hover:bg-rui-grey-800"
          data-testid="dashboard-source-legend-liabilities"
          @click="emit('jump', 'liabilities')"
        >
          <span />
          <span class="flex items-center gap-1">
            {{ t('dashboard.liabilities.title') }}
            <RuiIcon
              name="lu-arrow-down"
              size="14"
              class="text-rui-text-secondary"
            />
          </span>
          <FiatDisplay
            class="text-right"
            :value="summary.liabilities.negated()"
          />
          <span />
        </button>
      </li>
      <li v-if="summary.emptyKinds.length > 0">
        <AddSourceMenu />
      </li>
    </template>
  </ul>
</template>
