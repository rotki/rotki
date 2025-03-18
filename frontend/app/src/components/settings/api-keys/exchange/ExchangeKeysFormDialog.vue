<script setup lang="ts">
import type { ExchangeFormData } from '@/types/exchanges';
import type { ComponentExposed } from 'vue-component-type-helpers';
import BigDialog from '@/components/dialogs/BigDialog.vue';
import ExchangeKeysForm from '@/components/settings/api-keys/exchange/ExchangeKeysForm.vue';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { assert } from '@rotki/common';

const modelValue = defineModel<ExchangeFormData | undefined>({ required: true });

const submitting = ref<boolean>(false);
const stateUpdated = ref<boolean>(false);
const form = useTemplateRef<ComponentExposed<typeof ExchangeKeysForm>>('form');

const { setupExchange } = useExchanges();
const { t } = useI18n();

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
  const exchange = get(modelValue);
  const success = await setupExchange({
    ...exchange,
    newName: exchange.name === exchange.newName ? undefined : exchange.newName,
  });

  set(submitting, false);
  if (success)
    set(modelValue, undefined);
}
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
    />
  </BigDialog>
</template>
