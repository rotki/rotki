<template>
  <settings-option
    #default="{ error, success, update }"
    setting="balanceSaveFrequency"
    :transform="transform"
    :error-message="tc('general_settings.validation.balance_frequency.error')"
    :success-message="successMessage"
    @finished="resetBalanceSaveFrequency"
  >
    <v-text-field
      v-model="balanceSaveFrequency"
      outlined
      min="1"
      :max="maxBalanceSaveFrequency"
      class="mt-2 general-settings__fields__balance-save-frequency"
      :label="tc('general_settings.labels.balance_saving_frequency')"
      type="number"
      :success-messages="success"
      :error-messages="
        error || v$.balanceSaveFrequency.$errors.map(e => e.$message)
      "
      @change="callIfValid($event, update)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useGeneralSettingsStore } from '@/store/settings/general';

const balanceSaveFrequency = ref<string>('0');

const { balanceSaveFrequency: frequency } = storeToRefs(
  useGeneralSettingsStore()
);

const { tc } = useI18n();

const maxBalanceSaveFrequency = Constraints.MAX_HOURS_DELAY;
const rules = {
  balanceSaveFrequency: {
    required: helpers.withMessage(
      tc('general_settings.validation.balance_frequency.non_empty'),
      required
    ),
    between: helpers.withMessage(
      tc('general_settings.validation.balance_frequency.invalid_frequency', 0, {
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

const transform = (value?: string) => (value ? parseInt(value) : value);
const successMessage = (frequency: string) =>
  tc('general_settings.validation.balance_frequency.success', 0, {
    frequency
  });

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>
