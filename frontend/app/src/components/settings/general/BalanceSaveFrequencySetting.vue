<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/data/constraints';
import { toMessages } from '@/utils/validation';

const balanceSaveFrequency = ref<string>('0');

const { balanceSaveFrequency: frequency } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const maxBalanceSaveFrequency = Constraints.MAX_HOURS_DELAY;
const rules = {
  balanceSaveFrequency: {
    required: helpers.withMessage(t('general_settings.balance_frequency.validation.non_empty'), required),
    between: helpers.withMessage(
      t('general_settings.balance_frequency.validation.invalid_frequency', {
        start: 1,
        end: maxBalanceSaveFrequency,
      }),
      between(1, maxBalanceSaveFrequency),
    ),
  },
};
const v$ = useVuelidate(rules, { balanceSaveFrequency }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetBalanceSaveFrequency() {
  set(balanceSaveFrequency, get(frequency).toString());
}

const transform = (value?: string) => (value ? Number.parseInt(value) : value);

function successMessage(frequency: string) {
  return t('general_settings.balance_frequency.validation.success', {
    frequency,
  });
}

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>

<template>
  <SettingsOption
    setting="balanceSaveFrequency"
    :transform="transform"
    :error-message="t('general_settings.balance_frequency.validation.error')"
    :success-message="successMessage"
    @finished="resetBalanceSaveFrequency()"
  >
    <template #title>
      {{ t('general_settings.balance_frequency.title') }}
    </template>
    <template
      #default="{ error, success, update }"
    >
      <RuiTextField
        v-model="balanceSaveFrequency"
        variant="outlined"
        color="primary"
        min="1"
        :max="maxBalanceSaveFrequency"
        class="general-settings__fields__balance-save-frequency"
        :label="t('general_settings.balance_frequency.label')"
        type="number"
        :success-messages="success"
        :error-messages="error || toMessages(v$.balanceSaveFrequency)"
        @update:model-value="callIfValid($event, update)"
      />
    </template>
  </SettingsOption>
</template>
