<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { BankConnectionIdentity, BankFormData } from '@/modules/banks/types';
import { assert } from '@rotki/common';
import BankConnectionForm from '@/modules/banks/components/BankConnectionForm.vue';
import { useBanks } from '@/modules/banks/use-banks';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
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
const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (!isDefined(modelValue))
    return '';
  return get(modelValue).mode === 'edit'
    ? t('bank_settings.dialog.edit.title')
    : t('bank_settings.dialog.add.title');
});

/** Credential slots are snake_case on the wire; the api error keys arrive camelCased. */
function toCamelCase(slot: string): string {
  return slot.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

/** The api reports credential errors under the slot; the form binds them at `credentials.<slot>`. */
function toFieldErrors(errors: ValidationErrors, form: BankFormData): ValidationErrors {
  const slotsByKey = new Map<string, string>(
    Object.keys(form.credentials).flatMap(slot => [[slot, slot], [toCamelCase(slot), slot]]),
  );
  const mapped: ValidationErrors = {};
  for (const [key, value] of Object.entries(errors)) {
    const slot = slotsByKey.get(key);
    mapped[slot === undefined ? key : `credentials.${slot}`] = value;
  }
  return mapped;
}

async function save(): Promise<void> {
  assert(isDefined(modelValue));
  if (!get(form)?.validate())
    return;

  set(submitting, true);
  set(errorMessages, {});
  const payload = get(modelValue);

  let success = false;
  try {
    success = await setupBank(payload);
  }
  catch (error: unknown) {
    let errors: string | ValidationErrors = getErrorMessage(error);
    if (error instanceof ApiValidationError) {
      errors = error.getValidationErrors({
        ...payload,
        ...Object.fromEntries(Object.entries(payload.credentials).map(([slot, value]) => [toCamelCase(slot), value])),
      });
    }

    if (typeof errors === 'string') {
      setMessage({
        description: t('bank_settings.errors.setup_message', { bank: payload.location, error: errors }),
        title: t('bank_settings.errors.setup_title'),
      });
    }
    else {
      set(errorMessages, toFieldErrors(errors, payload));
    }
  }

  set(submitting, false);
  if (success) {
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
