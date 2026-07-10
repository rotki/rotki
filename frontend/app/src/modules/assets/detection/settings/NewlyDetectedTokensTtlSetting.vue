<script setup lang="ts">
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/modules/core/common/constraints';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const minTtlDays = Constraints.NEWLY_DETECTED_TOKENS_MIN_TTL_DAYS;
const maxTtlDays = Constraints.NEWLY_DETECTED_TOKENS_MAX_TTL_DAYS;

const rules = {
  value: {
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
</script>

<template>
  <SettingNumber
    class="mt-1"
    setting="newlyDetectedTokensTtlDays"
    :rules="rules"
    :label="t('frontend_settings.newly_detected_tokens.ttl_days.label')"
    :hint="t('frontend_settings.newly_detected_tokens.ttl_days.hint')"
    :error-message="t('frontend_settings.newly_detected_tokens.ttl_days.validation.error')"
  />
</template>
