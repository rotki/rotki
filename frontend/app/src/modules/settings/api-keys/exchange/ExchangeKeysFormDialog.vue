<script setup lang="ts">
import type { ComponentExposed } from 'vue-component-type-helpers';
import type { ExchangeFormData } from '@/modules/balances/types/exchanges';
import { assert } from '@rotki/common';
import { useBinancePairsConditions } from '@/modules/balances/exchanges/use-binance-pairs-conditions';
import { useExchangeKeyConditions } from '@/modules/balances/exchanges/use-exchange-key-conditions';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useSaveFailure } from '@/modules/core/form/use-save-failure';
import ExchangeKeysForm from '@/modules/settings/api-keys/exchange/ExchangeKeysForm.vue';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';

const modelValue = defineModel<ExchangeFormData | undefined>({ required: true });

const emit = defineEmits<{
  added: [exchange: { location: string; name: string }];
}>();

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<ComponentExposed<typeof ExchangeKeysForm>>('form');

const { setupExchange } = useExchanges();
const { settleSaved } = useBinancePairsConditions();
const { settleSaved: settleSavedKey } = useExchangeKeyConditions();
const { capture, clear, failure, modelFieldErrors } = useSaveFailure();
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
  if (!get(form)?.validate()) {
    return;
  }

  set(submitting, true);
  clear();

  const exchange = get(modelValue);
  const payload = {
    ...exchange,
    newName: exchange.name === exchange.newName ? undefined : exchange.newName,
  };

  let success = false;
  try {
    await setupExchange(payload);
    success = true;
    settleSaved(payload);
    settleSavedKey(payload);
  }
  catch (error: unknown) {
    capture(error, payload);
  }

  set(submitting, false);
  if (success) {
    if (exchange.mode !== 'edit')
      emit('added', { location: exchange.location, name: exchange.name });
    set(modelValue, undefined);
  }
}

watch(modelValue, (modelValue) => {
  if (!modelValue)
    clear();
});
</script>

<template>
  <BigDialog
    :display="!!modelValue"
    :title="title"
    :action="{ primary: t('common.actions.save') }"
    :loading="submitting"
    :prompt-on-close="stateUpdated"
    :failure="failure"
    :failure-title="t('actions.balances.exchange_setup.title')"
    @confirm="save()"
    @cancel="modelValue = undefined"
  >
    <ExchangeKeysForm
      v-if="modelValue"
      ref="form"
      v-model="modelValue"
      v-model:state-updated="stateUpdated"
      v-model:error-messages="modelFieldErrors"
    />
  </BigDialog>
</template>
