<script setup lang="ts">
import type { RuiTextField } from '@rotki/ui-library';
import type { ValidationErrors } from '@/types/api/errors';
import useVuelidate from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import { useFormStateWatcher } from '@/composables/form';
import { toMessages } from '@/utils/validation';

const errors = defineModel<ValidationErrors>('errorMessages', { required: true });
const stateUpdated = defineModel<boolean>('stateUpdated', { default: false, required: false });
const modelValue = defineModel<string>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const rules = {
  modelValue: { required },
};

const states = {
  modelValue,
};

const v$ = useVuelidate(
  rules,
  states,
  {
    $autoDirty: true,
    $externalResults: errors,
  },
);

useFormStateWatcher(states, stateUpdated);

defineExpose({
  validate: async () => await get(v$).$validate(),
});
</script>

<template>
  <RuiTextField
    v-model="modelValue"
    variant="outlined"
    color="primary"
    class="pt-2"
    :label="t('general_settings.labels.node_rpc_endpoint')"
    type="text"
    clearable
    :error-messages="toMessages(v$.modelValue)"
  />
</template>
