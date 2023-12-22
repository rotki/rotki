<script setup lang="ts">
import { StepperState } from '@rotki/ui-library-compat';
import { type EvmTransactionQueryData } from '@/types/websocket-messages';

const props = defineProps<{ item: EvmTransactionQueryData }>();

const { t } = useI18n();

const { item } = toRefs(props);

const steps = computed(() => {
  const itemVal = get(item);
  const steps = [
    toSentenceCase(
      t('transactions.query_status.statuses.querying_transactions')
    ),
    toSentenceCase(
      t('transactions.query_status.statuses.querying_internal_transactions')
    ),
    toSentenceCase(
      t('transactions.query_status.statuses.querying_evm_tokens_transactions')
    )
  ];

  return steps.map((title, index) => ({
    title,
    state: isStepCompleted(itemVal, index)
      ? StepperState.done
      : StepperState.inactive,
    loading: isStepInProgress(itemVal, index)
  }));
});

const { getStatusData } = useTransactionQueryStatus();

const isStepCompleted = (item: EvmTransactionQueryData, stepIndex: number) =>
  getStatusData(item).index > stepIndex + 1;

const isStepInProgress = (item: EvmTransactionQueryData, stepIndex: number) =>
  getStatusData(item).index === stepIndex + 1;
</script>

<template>
  <RuiStepper class="-mx-4 [&_hr]:!hidden" :steps="steps" />
</template>
