<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BankConnectionIdentity, BankFormData, BankSetupError } from '@/modules/banks/types';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { assert } from '@rotki/common';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { useBanks } from '@/modules/banks/use-banks';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<BankFormData | undefined>({ required: true });

const emit = defineEmits<{
  added: [connection: BankConnectionIdentity];
}>();

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const errorMessages = ref<ValidationErrors>({});
const form = useTemplateRef<ComponentExposed<typeof BankConnectionForm>>('form');

const { setupBank } = useBanks();
const { bankNameFor } = useBankConnectionsStore();
const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (!isDefined(modelValue))
    return '';
  return get(modelValue).mode === 'edit'
    ? t('bank_settings.dialog.edit.title')
    : t('bank_settings.dialog.add.title');
});

/** The api keys credential errors by slot; the form binds them at `credentials.<slot>`. */
function toFieldErrors(errors: ValidationErrors, form: BankFormData): ValidationErrors {
  return Object.fromEntries(
    Object.entries(errors).map(([key, value]) => [Object.hasOwn(form.credentials, key) ? `credentials.${key}` : key, value]),
  );
}

function showSetupError(error: BankSetupError, payload: BankFormData): void {
  if (error.type === 'fields') {
    set(errorMessages, toFieldErrors(error.errors, payload));
    return;
  }
  setMessage({
    description: t('bank_settings.errors.setup_message', { bank: bankNameFor(payload.location), error: error.message }),
    title: t('bank_settings.errors.setup_title'),
  });
}

async function save(): Promise<void> {
  assert(isDefined(modelValue));
  if (!get(form)?.validate())
    return;

  set(submitting, true);
  set(errorMessages, {});
  const payload = get(modelValue);
  const outcome = await setupBank(payload);
  set(submitting, false);

  if (!outcome.ok) {
    showSetupError(outcome.error, payload);
    return;
  }

  if (outcome.value) {
    if (payload.mode !== 'edit')
      emit('added', { location: payload.location, name: payload.name });
    set(modelValue, undefined);
  }
}

watch(modelValue, (value) => {
  if (!value)
    set(errorMessages, {});
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="title"
    :action="{ primary: t('common.actions.save') }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <BankConnectionForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      v-model:error-messages="errorMessages"
    />
  </BigDialog>
</template>
