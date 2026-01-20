<script lang="ts" setup>
import type { Exchange } from '@/types/exchanges';
import type { RepullingExchangeEventsPayload, RepullingTransactionPayload } from '@/types/history/events';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RepullingTransactionForm from '@/components/history/events/tx/RepullingTransactionForm.vue';
import { type RepullingTransactionResult, useHistoryTransactions } from '@/composables/history/events/tx';
import { useRepullingTransactionForm } from '@/composables/history/events/tx/use-repulling-transaction-form';
import { HISTORY_EVENT_ACTIONS, type HistoryEventAction } from '@/composables/history/events/types';
import { useConfirmStore } from '@/store/confirm';
import { useHistoryStore } from '@/store/history';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

const modelValue = defineModel<boolean>({ required: true });
const currentAction = defineModel<HistoryEventAction>('currentAction', { required: true });

const props = withDefaults(defineProps<{
  loading?: boolean;
  repullTransactions?: (result: RepullingTransactionResult) => void;
  repullExchangeEvents?: (exchanges: Exchange[]) => void;
}>(), {
  loading: false,
});

const { t } = useI18n({ useScope: 'global' });

const accountType = ref<'blockchain' | 'exchange'>('blockchain');

const submitting = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof RepullingTransactionForm>>('form');
const stateUpdated = ref<boolean>(false);

const { setMessage } = useMessageStore();
const { show } = useConfirmStore();
const { repullingExchangeEvents, repullingTransactions } = useHistoryTransactions();
const { useIsTaskRunning } = useTaskStore();
const { createDefaultFormData, shouldShowConfirmation } = useRepullingTransactionForm();
const { resetUndecodedTransactionsStatus } = useHistoryStore();

const taskRunning = useIsTaskRunning(TaskType.REPULLING_TXS);

const formData = ref(createDefaultFormData());

function resetForm(): void {
  set(formData, createDefaultFormData());
  set(accountType, 'blockchain');
}

async function handleSubmissionError(
  error: any,
  data: RepullingTransactionPayload,
  formRef: InstanceType<typeof RepullingTransactionForm> | null,
): Promise<void> {
  let message: string | Record<string, string[] | string> = error.message;

  if (error instanceof ApiValidationError)
    message = error.getValidationErrors(data);

  if (typeof message === 'string') {
    setMessage({
      description: message,
    });
  }
  else {
    set(errorMessages, message);
    await formRef?.validate();
  }
}

async function handleExchangeSubmission(
  data: RepullingTransactionPayload,
  formRef: InstanceType<typeof RepullingTransactionForm> | null,
): Promise<void> {
  const exchange = formRef?.getExchangeData();
  const exchangePayload: RepullingExchangeEventsPayload = {
    fromTimestamp: data.fromTimestamp,
    location: exchange?.location || '',
    name: exchange?.name || '',
    toTimestamp: data.toTimestamp,
  };

  set(currentAction, HISTORY_EVENT_ACTIONS.REPULLING);
  const newEventsDetected = await repullingExchangeEvents(exchangePayload);
  if (newEventsDetected && exchange) {
    props.repullExchangeEvents?.([exchange]);
    logger.debug('New exchange events detected');
  }
}

async function handleBlockchainSubmission(data: RepullingTransactionPayload): Promise<void> {
  const chain = data.chain === 'all' ? undefined : data.chain;
  const blockchainPayload: RepullingTransactionPayload = {
    address: data.address,
    chain,
    fromTimestamp: data.fromTimestamp,
    toTimestamp: data.toTimestamp,
  };

  set(currentAction, HISTORY_EVENT_ACTIONS.REPULLING);
  resetUndecodedTransactionsStatus();
  const result = await repullingTransactions(blockchainPayload);
  if (result) {
    props.repullTransactions?.(result);
    logger.debug(`New transactions detected${chain ? ` for chain ${chain}` : ' for all chains'}`);
  }
}

async function performSubmission(): Promise<void> {
  const formRef = get(form);
  const data = get(formData);
  const type = get(accountType);

  try {
    set(submitting, true);
    set(modelValue, false);

    if (type === 'exchange')
      await handleExchangeSubmission(data, formRef);
    else
      await handleBlockchainSubmission(data);

    resetForm();
  }
  catch (error: any) {
    await handleSubmissionError(error, data, formRef);
  }
  finally {
    set(submitting, false);
  }
}

async function submit(): Promise<void> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return;

  const data = get(formData);
  const type = get(accountType);

  if (type === 'blockchain' && shouldShowConfirmation(data)) {
    show({
      message: t('transactions.repulling.confirmation.message'),
      title: t('transactions.repulling.confirmation.title'),
      type: 'info',
    }, performSubmission);
  }
  else {
    await performSubmission();
  }
}
</script>

<template>
  <BigDialog
    :display="modelValue"
    :title="t('transactions.repulling.action')"
    :primary-action="t('transactions.repulling.action')"
    :action-disabled="loading || taskRunning"
    :action-tooltip="loading ? t('transactions.repulling.loading_tooltip') : ''"
    :loading="submitting || taskRunning"
    :prompt-on-close="stateUpdated"
    @confirm="submit()"
    @cancel="modelValue = false"
  >
    <RepullingTransactionForm
      ref="form"
      v-model="formData"
      v-model:account-type="accountType"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>
