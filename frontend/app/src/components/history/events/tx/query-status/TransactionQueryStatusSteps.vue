<script setup lang="ts">
import { TaskType } from '@/types/task-type';
import type { EvmTransactionQueryData } from '@/types/websocket-messages';

const props = defineProps<{ item: EvmTransactionQueryData }>();

const { t } = useI18n();
const { getStatusData } = useTransactionQueryStatus();
const { isTaskRunning } = useTaskStore();
const { isSmAndDown } = useBreakpoint();

const { item } = toRefs(props);

const transactionsLoading = isTaskRunning(TaskType.TX);

const stepList = computed(() => [
  t('transactions.query_status.statuses.querying_transactions'),
  t('transactions.query_status.statuses.querying_internal_transactions'),
  t('transactions.query_status.statuses.querying_evm_tokens_transactions'),
]);

const steps = computed(() =>
  get(stepList).map((step, index) => ({
    title: toSentenceCase(step),
    loading: isStepInProgress(index),
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
    class="[&_hr]:!hidden [&>div]:!py-0"
    :class="[isSmAndDown ? 'ml-8' : 'ml-2']"
    :steps="steps"
    :step="getStatusData(item).index"
    :orientation="isSmAndDown ? 'vertical' : 'horizontal'"
  />
</template>
