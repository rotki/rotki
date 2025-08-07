<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { ExchangeFormData } from '@/types/exchanges';
import { assert } from '@rotki/common';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ExchangeKeysForm from '@/components/settings/api-keys/exchange/ExchangeKeysForm.vue';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useMessageStore } from '@/store/message';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

const modelValue = defineModel<ExchangeFormData | undefined>({ required: true });

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const errorMessages = ref<ValidationErrors>({});
const form = useTemplateRef<ComponentExposed<typeof ExchangeKeysForm>>('form');

const { setupExchange } = useExchanges();
const { setMessage } = useMessageStore();
const { t } = useI18n({ useScope: 'global' });

const title = computed<string>(() => {
  if (!isDefined(modelValue)) {
    return '';
  }
  const { mode } = get(modelValue);
  return mode === 'edit' ? t('exchange_settings.dialog.edit.title') : t('exchange_settings.dialog.add.title');
});

async function save(): Promise<void> {
  assert(isDefined(modelValue));
  if (!await get(form)?.validate()) {
    return;
  }

  set(submitting, true);
  set(errorMessages, {});

  const exchange = get(modelValue);
  const payload = {
    ...exchange,
    newName: exchange.name === exchange.newName ? undefined : exchange.newName,
  };

  let success = false;
  try {
    success = await setupExchange(payload);
  }
  catch (error: any) {
    let errors = error.message;

    if (error instanceof ApiValidationError) {
      errors = error.getValidationErrors(payload);
    }

    if (typeof errors === 'string') {
      setMessage({
        description: t('actions.balances.exchange_setup.description', {
          error: errors,
          exchange: payload.location,
        }),
        title: t('actions.balances.exchange_setup.title'),
      });
    }
    else {
      set(errorMessages, errors);
    }
  }

  set(submitting, false);
  if (success) {
    set(modelValue, undefined);
  }
}

watch(modelValue, (modelValue) => {
  if (!modelValue) {
    set(errorMessages, {});
  }
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="title"
    :primary-action="t('common.actions.save')"
    :secondary-action="t('common.actions.cancel')"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ExchangeKeysForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      v-model:error-messages="errorMessages"
    />
  </BigDialog>
</template>
