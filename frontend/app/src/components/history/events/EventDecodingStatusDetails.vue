<script setup lang="ts">
import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const props = defineProps<{ item: EvmUnDecodedTransactionsData }>();

const { t } = useI18n();

const { isTaskRunning } = useTaskStore();

const remaining = computed<number>(() => props.item.total - props.item.processed);

const isComplete = computed<boolean>(() => get(remaining) === 0);

const decoding = computed<boolean>(() =>
  get(isTaskRunning(TaskType.TRANSACTIONS_DECODING, { chain: props.item.chain })),
);
</script>

<template>
  <div class="flex items-center gap-2">
    <AdaptiveWrapper>
      <EvmChainIcon
        :chain="item.chain"
        size="1.25rem"
      />
    </AdaptiveWrapper>
    <div class="flex flex-wrap text-body-2">
      <template v-if="isComplete">
        {{ t('transactions.events_decoding.decoding.done', { count: item.total }) }}
      </template>
      <template v-else-if="!decoding">
        {{ t('transactions.events_decoding.decoding.pending', { count: remaining }) }}
      </template>
      <template v-else>
        {{ t('transactions.events_decoding.decoding.processing', { count: item.processed, total: item.total }) }}
      </template>
    </div>
  </div>
</template>
