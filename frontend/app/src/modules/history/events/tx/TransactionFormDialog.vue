<script lang="ts" setup>
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { AddTransactionHashPayload, LocationAndTxRef } from '@/modules/history/events/event-payloads';
import { useTemplateRef } from 'vue';
import TransactionForm from '@/modules/history/events/tx/TransactionForm.vue';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<AddTransactionHashPayload | undefined>({ required: true });

const { loading = false } = defineProps<{
  loading?: boolean;
}>();

const emit = defineEmits<{
  reload: [event: LocationAndTxRef];
}>();

const { t } = useI18n({ useScope: 'global' });

const submitting = ref<boolean>(false);
const errorMessages = ref<ValidationErrors>({});
const form = useTemplateRef<InstanceType<typeof TransactionForm>>('form');
const stateUpdated = ref<boolean>(false);
/** Why the last save failed where no field is to blame; the form keeps what was typed. */
const saveFailure = shallowRef<string>();

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
  set(saveFailure, undefined);
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
      set(saveFailure, result.message);
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
    :action="{ disabled: loading, primary: t('common.actions.save') }"
    :layout="{ autoHeight: true, maxWidth: '640px' }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    :failure="saveFailure"
    :failure-title="t('transactions.dialog.add_tx_error')"
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
