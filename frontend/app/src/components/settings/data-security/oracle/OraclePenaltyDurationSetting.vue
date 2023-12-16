<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';
import { toMessages } from '@/utils/validation';

const oraclePenaltyDuration = ref<string>('0');

const { oraclePenaltyDuration: frequency } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const min = 1;
const rules = {
  oraclePenaltyDuration: {
    required: helpers.withMessage(
      t('oracle_cache_management.penalty.validation.oracle_penalty_duration.non_empty'),
      required,
    ),
    min: helpers.withMessage(
      t('oracle_cache_management.penalty.validation.oracle_penalty_duration.invalid_period', { min }),
      minValue(min),
    ),
  },
};
const v$ = useVuelidate(rules, { oraclePenaltyDuration }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetBalanceSaveFrequency() {
  set(oraclePenaltyDuration, get(frequency).toString());
}

const transform = (value?: string) => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="oraclePenaltyDuration"
    :transform="transform"
    @finished="resetBalanceSaveFrequency()"
  >
    <RuiTextField
      v-model="oraclePenaltyDuration"
      variant="outlined"
      color="primary"
      :min="min"
      class="mt-2"
      :label="t('oracle_cache_management.penalty.labels.oracle_penalty_duration')"
      :hint="t('oracle_cache_management.penalty.hints.oracle_penalty_duration')"
      type="number"
      :success-messages="success"
      :error-messages="error || toMessages(v$.oraclePenaltyDuration)"
      @update:model-value="callIfValid($event, update)"
    />
  </SettingsOption>
</template>
