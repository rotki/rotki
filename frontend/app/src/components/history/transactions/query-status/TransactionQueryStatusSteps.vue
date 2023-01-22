<script setup lang="ts">
import { toSentenceCase } from '@/utils/text';
import { type EvmTransactionQueryData } from '@/types/websocket-messages';

defineProps<{ item: EvmTransactionQueryData }>();

const { tc } = useI18n();

const steps = computed(() => [
  toSentenceCase(
    tc('transactions.query_status.statuses.querying_transactions')
  ),
  toSentenceCase(
    tc('transactions.query_status.statuses.querying_internal_transactions')
  ),
  toSentenceCase(
    tc('transactions.query_status.statuses.querying_evm_tokens_transactions')
  )
]);

const { getStatusData } = useTransactionQueryStatus();

const isStepCompleted = (item: EvmTransactionQueryData, stepIndex: number) => {
  return getStatusData(item).index > stepIndex + 1;
};

const isStepInProgress = (item: EvmTransactionQueryData, stepIndex: number) => {
  return getStatusData(item).index === stepIndex + 1;
};

const css = useCssModule();
</script>

<template>
  <v-stepper vertical flat :value="-1" :class="css.stepper">
    <v-stepper-header :class="css['stepper__header']">
      <template v-for="(step, index) in steps">
        <v-stepper-step
          :key="step"
          :class="css['stepper__item']"
          :step="index + 1"
          color="green"
          :complete="isStepCompleted(item, index)"
        >
          <div :class="isStepCompleted(item, index) ? 'green--text' : ''">
            {{ step }}
          </div>
          <v-progress-circular
            v-if="isStepInProgress(item, index)"
            :class="css['stepper__progress']"
            size="32"
            indeterminate
            width="2"
            color="primary"
          />
        </v-stepper-step>
      </template>
    </v-stepper-header>
  </v-stepper>
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
