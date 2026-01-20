<script setup lang="ts">
import type { ProtocolCacheProgress } from '../types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import { useSupportedChains } from '@/composables/info/chains';

const props = withDefaults(defineProps<{
  item: ProtocolCacheProgress;
  compact?: boolean;
}>(), {
  compact: false,
});

const { t } = useI18n({ useScope: 'global' });
const { getChainName } = useSupportedChains();

const chainName = getChainName(computed(() => props.item.chain));

const isComplete = computed<boolean>(() => props.item.processed >= props.item.total);
const isPending = computed<boolean>(() => props.item.processed === 0 && props.item.total > 0);
const isInProgress = computed<boolean>(() => props.item.processed > 0 && props.item.processed < props.item.total);

const statusIcon = computed<string>(() => {
  if (get(isComplete))
    return 'lu-check';
  if (get(isPending))
    return 'lu-circle';
  return 'lu-loader-circle';
});

const statusColor = computed<string>(() => {
  if (get(isComplete))
    return 'text-rui-success';
  if (get(isPending))
    return 'text-rui-text-disabled';
  return 'text-rui-primary';
});

const statusText = computed<string>(() => {
  if (get(isComplete))
    return t('sync_progress.status.complete');
  if (get(isPending))
    return t('sync_progress.status.pending');
  return t('sync_progress.status.refreshing');
});

const progressColor = computed<'success' | 'secondary' | 'primary'>(() => {
  if (get(isComplete))
    return 'success';
  if (get(isPending))
    return 'secondary';
  return 'primary';
});

const statusBorderColor = computed<string>(() => {
  if (get(isComplete))
    return 'border-l-rui-success';
  if (get(isInProgress))
    return 'border-l-rui-primary';
  return 'border-l-rui-grey-400 dark:border-l-rui-grey-600';
});
</script>

<template>
  <div
    class="flex items-center gap-3 px-2 rounded-r border-l-2 hover:bg-rui-grey-100 dark:hover:bg-rui-grey-700 transition-colors"
    :class="[statusBorderColor, compact ? 'py-1' : 'py-2', { 'animate-pulse bg-rui-primary/5': isInProgress }]"
  >
    <ChainIcon
      :chain="item.chain"
      :size="compact ? '1rem' : '1.25rem'"
    />

    <div class="flex-1 min-w-0 flex items-center gap-2">
      <span
        class="font-medium text-rui-text truncate"
        :class="compact ? 'text-xs' : 'text-sm'"
      >
        {{ chainName }}
      </span>
      <span
        class="text-rui-text-secondary"
        :class="compact ? 'text-xs' : 'text-sm'"
      >
        /
      </span>
      <CounterpartyDisplay
        :counterparty="item.protocol"
        :size="compact ? '0.75rem' : '1rem'"
        class="min-w-0"
        :class="compact ? 'text-xs' : 'text-sm'"
      />
    </div>

    <div
      v-if="!compact"
      class="w-24"
    >
      <RuiProgress
        :value="item.progress"
        :color="progressColor"
        size="sm"
        rounded
      />
    </div>

    <span
      class="text-rui-text-secondary tabular-nums whitespace-nowrap"
      :class="compact ? 'text-xs' : 'text-sm'"
    >
      {{ t('sync_progress.protocol_cache_progress', { processed: item.processed, total: item.total }) }}
    </span>

    <span
      class="text-rui-text-secondary whitespace-nowrap"
      :class="compact ? 'text-[10px]' : 'text-xs'"
    >
      {{ statusText }}
    </span>

    <RuiIcon
      :name="statusIcon"
      :class="[statusColor, { 'animate-spin': isInProgress }]"
      :size="compact ? 12 : 16"
    />
  </div>
</template>
