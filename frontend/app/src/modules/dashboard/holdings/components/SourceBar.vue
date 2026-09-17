<script setup lang="ts">
import type { SourceTotal, SummaryKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { barWeights } from '@/modules/dashboard/holdings/core/source-summary';
import { SOURCE_KIND_COLOR } from '@/modules/dashboard/holdings/source-kind-style';

const { selectedKind, showShares, sources } = defineProps<{
  sources: readonly SourceTotal[];
  /** When off, segments are equal so their widths reveal nothing. */
  showShares: boolean;
  selectedKind?: SummaryKind;
  label: string;
}>();

const segments = computed<{ kind: SummaryKind; weight: number }[]>(() => {
  const weights = barWeights(sources, showShares);
  return sources.map((source, index) => ({ kind: source.kind, weight: weights[index] }));
});
</script>

<template>
  <div
    role="img"
    :aria-label="label"
    class="flex gap-0.5 h-2.5"
    data-testid="dashboard-source-bar"
  >
    <div
      v-for="segment in segments"
      :key="segment.kind"
      class="h-full min-w-1 first:rounded-l last:rounded-r transition-opacity"
      :class="[SOURCE_KIND_COLOR[segment.kind], { 'opacity-25': selectedKind && selectedKind !== segment.kind }]"
      :style="{ flexGrow: segment.weight }"
      :data-kind="segment.kind"
    />
  </div>
</template>
