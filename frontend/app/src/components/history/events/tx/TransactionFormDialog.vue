<script lang="ts" setup>
import type { AddTransactionHashPayload, LocationAndTxRef } from '@/types/history/events';
import { useTemplateRef } from 'vue';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import TransactionForm from '@/components/history/events/tx/TransactionForm.vue';
import { useHistoryTransactions } from '@/composables/history/events/tx';
import { useMessageStore } from '@/store/message';

const modelValue = defineModel<AddTransactionHashPayload | undefined>({ required: true });

withDefaults(
  defineProps<{
    loading?: boolean;
  }>(),
  {
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'reload', event: LocationAndTxRef): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref<boolean>(false);
const errorMessages = ref<Record<string, string[]>>({});
const form = useTemplateRef<InstanceType<typeof TransactionForm>>('form');
const stateUpdated = ref(false);

const { setMessage } = useMessageStore();
const { addTransactionHash } = useHistoryTransactions();

async function save() {
  if (!isDefined(modelValue))
    return false;

  const formRef = get(form);
  const valid = await formRef?.validate();
  if (!valid)
    return false;

  const payload = get(modelValue);

  set(submitting, true);
  const result = await addTransactionHash(payload);
  set(submitting, false);

  if (result.success) {
    set(modelValue, undefined);
    emit('reload', {
      location: payload.blockchain,
      txRef: payload.txRef,
    });
  }
  else if (result.message) {
    if (typeof result.message === 'string') {
      setMessage({
        description: result.message,
      });
    }
    else {
      set(errorMessages, result.message);
      await formRef?.validate();
    }
  }
}
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="t('transactions.dialog.add_tx')"
    :primary-action="t('common.actions.save')"
    :action-disabled="loading"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <TransactionForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:error-messages="errorMessages"
      v-model:state-updated="stateUpdated"
    />
  </BigDialog>
</template>
