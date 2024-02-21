<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';
import type { EvmTransactionQueryData } from '@/types/websocket-messages';

const props = defineProps<{ item: EvmTransactionQueryData }>();

const { t } = useI18n();
const { getStatusData } = useTransactionQueryStatus();
const { isSmAndDown } = useBreakpoint();

const { item } = toRefs(props);

const steps = computed(() => {
  const steps = [
    t('transactions.query_status.statuses.querying_transactions'),
    t('transactions.query_status.statuses.querying_internal_transactions'),
    t('transactions.query_status.statuses.querying_evm_tokens_transactions'),
  ];

  const itemVal = get(item);

  return steps.map((step, index) => ({
    title: toSentenceCase(step),
    loading: isStepInProgress(itemVal, index),
  }));
});

const hasProgress = computed(() => get(steps).some(step => step.loading));

function isStepInProgress(item: EvmTransactionQueryData, stepIndex: number) {
  return getStatusData(item).index === stepIndex + 1;
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
