<template>
  <settings-option
    #default="{ error, success, update }"
    setting="balanceSaveFrequency"
    :transform="value => (value ? parseInt(value) : value)"
    :error-message="$tc('general_settings.validation.balance_frequency.error')"
    :success-message="
      frequency =>
        $tc('general_settings.validation.balance_frequency.success', 0, {
          frequency
        })
    "
    @finished="resetBalanceSaveFrequency"
  >
    <v-text-field
      v-model="balanceSaveFrequency"
      outlined
      min="1"
      :max="maxBalanceSaveFrequency"
      class="mt-2 general-settings__fields__balance-save-frequency"
      :label="$t('general_settings.labels.balance_saving_frequency')"
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
import { useSettings } from '@/composables/settings';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import i18n from '@/i18n';

const balanceSaveFrequency = ref<string>('0');

const { generalSettings } = useSettings();

const maxBalanceSaveFrequency = Constraints.MAX_HOURS_DELAY;
const rules = {
  balanceSaveFrequency: {
    required: helpers.withMessage(
      i18n
        .t('general_settings.validation.balance_frequency.non_empty')
        .toString(),
      required
    ),
    between: helpers.withMessage(
      i18n
        .t('general_settings.validation.balance_frequency.invalid_frequency', {
          start: 1,
          end: maxBalanceSaveFrequency
        })
        .toString(),
      between(1, maxBalanceSaveFrequency)
    )
  }
};
const v$ = useVuelidate(rules, { balanceSaveFrequency }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const resetBalanceSaveFrequency = () => {
  const settings = get(generalSettings);
  set(balanceSaveFrequency, settings.balanceSaveFrequency.toString());
};

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>
