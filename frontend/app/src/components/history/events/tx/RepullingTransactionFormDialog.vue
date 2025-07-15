<script lang="ts" setup>
import type { RepullingTransactionPayload } from '@/types/history/events';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import RepullingTransactionForm from '@/components/history/events/tx/RepullingTransactionForm.vue';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useSupportedChains } from '@/composables/info/chains';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';

const modelValue = defineModel<RepullingTransactionPayload | undefined>({ required: true });

withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof RepullingTransactionForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { repullingTransactions } = useHistoryTransactions();
const { getEvmChainName } = useSupportedChains();
const { useIsTaskRunning } = useTaskStore();

const taskRunning = useIsTaskRunning(TaskType.REPULLING_TXS);

async function submit() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const data = get(modelValue);
  const evmChainVal = data.evmChain;

  const evmChain = evmChainVal && evmChainVal !== 'evm' ? getEvmChainName(evmChainVal) : undefined;
  const payload: RepullingTransactionPayload = {
    ...data,
    address: data.address || undefined,
    evmChain,
  };

  try {
    set(submitting, true);
    await repullingTransactions(payload, () => emit('refresh'));
    set(submitting, false);
    set(modelValue, undefined);
  }
  catch (error: any) {
    let message = error.message;
    if (error instanceof ApiValidationError)
      message = error.getValidationErrors(payload);

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
  finally {
    set(submitting, false);
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="t('transactions.repulling.title')"
    :primary-action="t('transactions.repulling.action')"
    :action-disabled="loading || taskRunning"
    :loading="submitting || taskRunning"
    :prompt-on-close="stateUpdated"
    @confirm="submit()"
    @cancel="modelValue = undefined"
  >
    <RepullingTransactionForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>
