<script lang="ts" setup>
import type { DialogEventHandlers } from '@/components/history/events/dialog-types';
import type { ChainAddress, RepullingExchangeEventsPayload, RepullingTransactionPayload } from '@/types/history/events';
import dayjs from 'dayjs';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RepullingTransactionForm from '@/components/history/events/tx/RepullingTransactionForm.vue';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { HISTORY_EVENT_ACTIONS, type HistoryEventAction } from '@/composables/history/events/types';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { logger } from '@/utils/logging';

const modelValue = defineModel<boolean>({ required: true });
const currentAction = defineModel<HistoryEventAction>('currentAction', { required: true });

const props = withDefaults(defineProps<{
  eventHandlers?: DialogEventHandlers;
  loading?: boolean;
}>(), {
  eventHandlers: () => ({}),
  loading: false,
});

const { t } = useI18n({ useScope: 'global' });

const accountType = ref<'blockchain' | 'exchange'>('blockchain');

const submitting = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof RepullingTransactionForm>>('form');
const stateUpdated = ref<boolean>(false);

const { setMessage } = useMessageStore();
const { repullingExchangeEvents, repullingTransactions } = useHistoryTransactions();
const { accounts: accountsPerChain } = storeToRefs(useBlockchainAccountsStore());
const { useIsTaskRunning } = useTaskStore();

const taskRunning = useIsTaskRunning(TaskType.REPULLING_TXS);

function defaultForm(): RepullingTransactionPayload {
  const accountChains = Object.entries(get(accountsPerChain))
    .filter(([_, accounts]) => accounts.length > 0)
    .map(([chain]) => chain);

  return {
    address: '',
    chain: accountChains[0],
    fromTimestamp: dayjs().subtract(1, 'year').unix(),
    toTimestamp: dayjs().unix(),
  };
}

const formData = ref<RepullingTransactionPayload>(defaultForm());

function resetForm(): void {
  set(formData, defaultForm());
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
    props.eventHandlers.onRepullExchangeEvents?.([exchange]);
    logger.debug('New exchange events detected');
  }
}

async function handleBlockchainSubmission(data: RepullingTransactionPayload): Promise<void> {
  const refreshPayload: ChainAddress = {
    address: data.address!,
    chain: data.chain,
  };
  const blockchainPayload: RepullingTransactionPayload = {
    ...refreshPayload,
    fromTimestamp: data.fromTimestamp,
    toTimestamp: data.toTimestamp,
  };

  set(currentAction, HISTORY_EVENT_ACTIONS.REPULLING);
  const newTransactionsDetected = await repullingTransactions(blockchainPayload);
  if (newTransactionsDetected) {
    props.eventHandlers.onRepullTransactions?.(refreshPayload);
    const chains = [data.chain];
    logger.debug(`New transactions detected ${chains.join(', ')}`);
  }
}

async function submit(): Promise<void> {
  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return;

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
</script>

<template>
  <BigDialog
    :display="modelValue"
    :title="t('transactions.repulling.action')"
    :primary-action="t('transactions.repulling.action')"
    :action-disabled="loading || taskRunning"
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
