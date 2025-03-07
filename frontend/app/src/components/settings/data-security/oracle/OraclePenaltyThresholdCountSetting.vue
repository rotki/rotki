<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { toMessages } from '@/utils/validation';
import useVuelidate from '@vuelidate/core';
import { helpers, minValue, required } from '@vuelidate/validators';

const oraclePenaltyThresholdCount = ref<string>('0');

const { oraclePenaltyThresholdCount: frequency } = storeToRefs(useGeneralSettingsStore());

const { t } = useI18n();

const min = 1;
const rules = {
  oraclePenaltyThresholdCount: {
    min: helpers.withMessage(
      t('oracle_cache_management.penalty.validation.oracle_penalty_threshold_count.invalid_period', { min }),
      minValue(min),
    ),
    required: helpers.withMessage(
      t('oracle_cache_management.penalty.validation.oracle_penalty_threshold_count.non_empty'),
      required,
    ),
  },
};
const v$ = useVuelidate(rules, { oraclePenaltyThresholdCount }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

function resetBalanceSaveFrequency() {
  set(oraclePenaltyThresholdCount, get(frequency).toString());
}

const transform = (value?: string) => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetBalanceSaveFrequency();
});
</script>

<template>
  <SettingsOption
    setting="oraclePenaltyThresholdCount"
    :transform="transform"
    @finished="resetBalanceSaveFrequency()"
  >
    <template #title>
      {{ t('oracle_cache_management.penalty.labels.oracle_penalty_threshold_count') }}
    </template>
    <template #subtitle>
      {{ t('oracle_cache_management.penalty.hints.oracle_penalty_threshold_count') }}
    </template>
    <template
      #default="{ error, success, update }"
    >
      <RuiTextField
        v-model="oraclePenaltyThresholdCount"
        variant="outlined"
        color="primary"
        :min="min"
        class="mt-2"
        :label="t('oracle_cache_management.penalty.labels.oracle_penalty_threshold_count')"
        type="number"
        :success-messages="success"
        :error-messages="error || toMessages(v$.oraclePenaltyThresholdCount)"
        @update:model-value="callIfValid($event, update)"
      />
    </template>
  </SettingsOption>
</template>
