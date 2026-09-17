<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

const { chain, processed, protocol, stopped = false, total } = defineProps<{
  /** The backend's spelling (`ethereum`). */
  chain: string;
  protocol: string;
  processed: number;
  total: number;
  /** Left unfinished by work that settled; it shows where it stopped rather than a bar still filling. */
  stopped?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { useChainName } = useSupportedChains();

const chainName = useChainName(() => chain);

const filling = computed<boolean>(() => !stopped && processed < total);

const percentage = computed<number>(() => (total > 0 ? Math.round((processed / total) * 100) : 0));
</script>

<template>
  <div
    class="flex items-center gap-2 min-w-0 text-xs leading-5"
    data-testid="dock-cache-row"
  >
    <ChainIcon
      class="shrink-0"
      :chain="chain"
      size="0.875rem"
    />
    <span class="truncate text-rui-text-secondary">{{ chainName }}</span>
    <span
      class="text-rui-text-disabled before:content-['/']"
      aria-hidden="true"
    />
    <CounterpartyDisplay
      class="min-w-0 !text-xs"
      :counterparty="protocol"
      size="0.75rem"
    />
    <div
      v-if="filling"
      class="h-1 w-12 shrink-0 ml-auto rounded-full bg-rui-grey-200 dark:bg-rui-grey-800 overflow-hidden"
    >
      <div
        class="h-full bg-rui-primary transition-[width] duration-500"
        :style="{ width: `${percentage}%` }"
      />
    </div>
    <span
      v-else-if="stopped"
      class="shrink-0 ml-auto text-rui-warning"
      data-testid="dock-cache-stopped"
    >
      {{ t('task_dock.detail.cache_stopped') }}
    </span>
    <span
      class="shrink-0 tabular-nums text-rui-text-secondary"
      :class="{ 'ml-auto': !filling && !stopped }"
    >
      {{ t('pending_task.steps', { current: processed, total }) }}
    </span>
  </div>
</template>
