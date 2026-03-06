<script setup lang="ts">
import type { EvmUnDecodedTransactionsData } from '@/modules/messaging/types';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

const { item } = defineProps<{ item: EvmUnDecodedTransactionsData }>();

const { t } = useI18n({ useScope: 'global' });

const { useIsTaskRunning } = useTaskStore();

const remaining = computed<number>(() => item.total - item.processed);
const isComplete = computed<boolean>(() => get(remaining) === 0);
const taskMeta = computed(() => ({
  chain: item.chain,
}));

const decoding = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING, taskMeta);
</script>

<template>
  <div class="flex items-center gap-2">
    <ChainIcon
      :chain="item.chain"
      size="1.5rem"
    />
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
