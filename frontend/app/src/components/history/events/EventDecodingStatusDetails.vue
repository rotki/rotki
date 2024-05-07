<script setup lang="ts">
import { TaskType } from '@/types/task-type';
import type { EvmUnDecodedTransactionsData } from '@/types/websocket-messages';

const props = defineProps<{ item: EvmUnDecodedTransactionsData }>();

const { t } = useI18n();

const { isTaskRunning } = useTaskStore();

const isComplete = computed<boolean>(() => props.item.total === props.item.processed);

const decoding = computed<boolean>(() => get(isTaskRunning(TaskType.TRANSACTIONS_DECODING, { chain: props.item.evmChain })));
</script>

<template>
  <div class="flex items-center gap-2">
    <AdaptiveWrapper>
      <EvmChainIcon
        :chain="item.evmChain"
        size="1.25rem"
      />
    </AdaptiveWrapper>
    <div class="flex flex-wrap text-body-2">
      <template v-if="isComplete">
        {{ t('transactions.events_decoding.decoding.done', { count: item.total }) }}
      </template>
      <template v-else-if="!decoding">
        {{ t('transactions.events_decoding.decoding.pending', { count: item.total }) }}
      </template>
      <template v-else>
        {{ t('transactions.events_decoding.decoding.processing', { count: item.processed, total: item.total }) }}
      </template>
    </div>
  </div>
</template>
