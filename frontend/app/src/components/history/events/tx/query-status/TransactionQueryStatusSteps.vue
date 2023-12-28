<script setup lang="ts">
import { type EvmTransactionQueryData } from '@/types/websocket-messages';

const props = defineProps<{ item: EvmTransactionQueryData }>();

const { t } = useI18n();

const { item } = toRefs(props);

const steps = computed(() => {
  const steps = [
    t('transactions.query_status.statuses.querying_transactions'),
    t('transactions.query_status.statuses.querying_internal_transactions'),
    t('transactions.query_status.statuses.querying_evm_tokens_transactions')
  ];

  const itemVal = get(item);

  return steps.map((step, index) => ({
    title: toSentenceCase(step),
    loading: isStepInProgress(itemVal, index)
  }));
});

const { getStatusData } = useTransactionQueryStatus();

const isStepInProgress = (item: EvmTransactionQueryData, stepIndex: number) =>
  getStatusData(item).index === stepIndex + 1;
</script>

<template>
  <RuiStepper
    class="-mx-4 [&_hr]:!hidden"
    :steps="steps"
    :step="getStatusData(item).index"
  />
</template>
