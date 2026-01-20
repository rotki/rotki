<script setup lang="ts">
import useVuelidate from '@vuelidate/core';
import { between, helpers, required } from '@vuelidate/validators';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useValidation } from '@/composables/validation';
import { Constraints } from '@/data/constraints';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { toMessages } from '@/utils/validation';

const ttlDays = ref<string>('30');

const { t } = useI18n({ useScope: 'global' });

const minTtlDays = Constraints.NEWLY_DETECTED_TOKENS_MIN_TTL_DAYS;
const maxTtlDays = Constraints.NEWLY_DETECTED_TOKENS_MAX_TTL_DAYS;

const rules = {
  ttlDays: {
    between: helpers.withMessage(
      t('frontend_settings.newly_detected_tokens.ttl_days.validation.invalid_range', {
        max: maxTtlDays,
        min: minTtlDays,
      }),
      between(minTtlDays, maxTtlDays),
    ),
    required: helpers.withMessage(t('frontend_settings.newly_detected_tokens.ttl_days.validation.non_empty'), required),
  },
};

const { newlyDetectedTokensTtlDays: currentTtlDays } = storeToRefs(useFrontendSettingsStore());

function resetTtlDays(): void {
  set(ttlDays, get(currentTtlDays).toString());
}

const v$ = useVuelidate(rules, { ttlDays }, { $autoDirty: true });
const { callIfValid } = useValidation(v$);

const transform = (value: string): number | string => (value ? Number.parseInt(value) : value);

onMounted(() => {
  resetTtlDays();
});
</script>

<template>
  <SettingsOption
    class="mt-1"
    setting="newlyDetectedTokensTtlDays"
    frontend-setting
    :transform="transform"
    :error-message="t('frontend_settings.newly_detected_tokens.ttl_days.validation.error')"
    @finished="resetTtlDays()"
  >
    <template #title>
      {{ t('frontend_settings.newly_detected_tokens.ttl_days.title') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiTextField
        v-model="ttlDays"
        variant="outlined"
        color="primary"
        :label="t('frontend_settings.newly_detected_tokens.ttl_days.label')"
        :hint="t('frontend_settings.newly_detected_tokens.ttl_days.hint')"
        type="number"
        :min="minTtlDays"
        :max="maxTtlDays"
        :success-messages="success"
        :error-messages="error || toMessages(v$.ttlDays)"
        @update:model-value="callIfValid($event, update)"
      />
    </template>
  </SettingsOption>
</template>
