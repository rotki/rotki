<script setup lang="ts">
import { type EvmTransactionQueryData } from '@/types/websocket-messages';

defineProps<{ item: EvmTransactionQueryData }>();

const { t } = useI18n();

const steps = computed(() => [
  toSentenceCase(t('transactions.query_status.statuses.querying_transactions')),
  toSentenceCase(
    t('transactions.query_status.statuses.querying_internal_transactions')
  ),
  toSentenceCase(
    t('transactions.query_status.statuses.querying_evm_tokens_transactions')
  )
]);

const { getStatusData } = useTransactionQueryStatus();

const isStepCompleted = (item: EvmTransactionQueryData, stepIndex: number) =>
  getStatusData(item).index > stepIndex + 1;

const isStepInProgress = (item: EvmTransactionQueryData, stepIndex: number) =>
  getStatusData(item).index === stepIndex + 1;

const css = useCssModule();
</script>

<template>
  <VStepper vertical flat :value="-1" :class="css.stepper">
    <VStepperHeader :class="css['stepper__header']">
      <template v-for="(step, index) in steps">
        <VStepperStep
          :key="step"
          :class="css['stepper__item']"
          :step="index + 1"
          color="green"
          :complete="isStepCompleted(item, index)"
        >
          <div :class="isStepCompleted(item, index) ? 'text-rui-success' : ''">
            {{ step }}
          </div>
          <RuiProgress
            v-if="isStepInProgress(item, index)"
            :class="css['stepper__progress']"
            size="32"
            variant="indeterminate"
            circular
            thickness="2"
            color="primary"
          />
        </VStepperStep>
      </template>
    </VStepperHeader>
  </VStepper>
</template>

<style module lang="scss">
.stepper {
  padding-bottom: 0;

  &__header {
    box-shadow: none;
    justify-content: flex-start;
    height: auto;
    padding-left: 0.5rem;

    @media (max-width: 900px) {
      flex-direction: column;
    }
  }

  &__item {
    padding: 0.5rem 1.5rem 0.5rem 0 !important;
  }

  &__progress {
    position: absolute;
    left: -4px;
    top: 50%;
    transform: translateY(-50%);
  }
}
</style>
