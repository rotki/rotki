<script setup lang="ts">
import type { EvmTransactionQueryData } from '@/types/websocket-messages';
import { useTransactionQueryStatus } from '@/composables/history/events/query-status/tx-query-status';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { toSentenceCase } from '@rotki/common';

const props = defineProps<{ item: EvmTransactionQueryData }>();

const { t } = useI18n();
const { getStatusData } = useTransactionQueryStatus();
const { useIsTaskRunning } = useTaskStore();
const { isMdAndDown } = useBreakpoint();

const { item } = toRefs(props);

const taskMeta = computed(() => {
  const data = get(item);
  return {
    address: data.address,
    chain: data.evmChain,
  };
});

const transactionsLoading = useIsTaskRunning(TaskType.TX, taskMeta);

const stepList = computed(() => [
  t('transactions.query_status.statuses.querying_transactions'),
  t('transactions.query_status.statuses.querying_internal_transactions'),
  t('transactions.query_status.statuses.querying_evm_tokens_transactions'),
]);

const steps = computed(() =>
  get(stepList).map((step, index) => ({
    loading: isStepInProgress(index),
    title: toSentenceCase(step),
  })),
);

const hasProgress = computed(() => get(steps).some(step => step.loading));

function isStepInProgress(stepIndex: number): boolean {
  if (getStatusData(get(item)).index === 4 && stepIndex === get(stepList).length - 1 && get(transactionsLoading))
    return true;

  return getStatusData(get(item)).index === stepIndex + 1;
}
</script>

<template>
  <RuiStepper
    v-if="hasProgress"
    class="overflow-visible [&_hr]:!hidden [&>div]:!py-0 -mt-2 md:-mt-3"
    :class="[isMdAndDown ? 'ml-8' : 'ml-2']"
    :steps="steps"
    :step="getStatusData(item).index"
    :orientation="isMdAndDown ? 'vertical' : 'horizontal'"
  />
</template>
