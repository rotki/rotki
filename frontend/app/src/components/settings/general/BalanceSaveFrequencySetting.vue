<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/data/constraints';

const balanceSaveFrequency = ref<string>('0');

const { balanceSaveFrequency: frequency } = storeToRefs(
  useGeneralSettingsStore()
);

const { t } = useI18n();

const maxBalanceSaveFrequency = Constraints.MAX_HOURS_DELAY;
const rules = {
  balanceSaveFrequency: {
    required: helpers.withMessage(
      t('general_settings.validation.balance_frequency.non_empty'),
      required
    ),
    between: helpers.withMessage(
      t('general_settings.validation.balance_frequency.invalid_frequency', {
        start: 1,
        end: maxBalanceSaveFrequency
      }),
      between(1, maxBalanceSaveFrequency)
    )
  }
};
const v$ = useVuelidate(rules, { balanceSaveFrequency }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const resetBalanceSaveFrequency = () => {
  set(balanceSaveFrequency, get(frequency).toString());
};

const transform = (value?: string) => (value ? Number.parseInt(value) : value);
const successMessage = (frequency: string) =>
  t('general_settings.validation.balance_frequency.success', {
    frequency
  });

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="balanceSaveFrequency"
    :transform="transform"
    :error-message="t('general_settings.validation.balance_frequency.error')"
    :success-message="successMessage"
    @finished="resetBalanceSaveFrequency()"
  >
    <v-text-field
      v-model="balanceSaveFrequency"
      outlined
      min="1"
      :max="maxBalanceSaveFrequency"
      class="mt-2 general-settings__fields__balance-save-frequency"
      :label="t('general_settings.labels.balance_saving_frequency')"
      type="number"
      :success-messages="success"
      :error-messages="
        error || v$.balanceSaveFrequency.$errors.map(e => e.$message)
      "
      @change="callIfValid($event, update)"
    />
  </settings-option>
</template>
