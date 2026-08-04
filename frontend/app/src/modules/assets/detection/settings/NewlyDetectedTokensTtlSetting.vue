<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import { numberSettingSchema } from '@/modules/settings/controls/setting-field-schemas';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const minTtlDays = Constraints.NEWLY_DETECTED_TOKENS_MIN_TTL_DAYS;
const maxTtlDays = Constraints.NEWLY_DETECTED_TOKENS_MAX_TTL_DAYS;

const schema = numberSettingSchema({
  max: maxTtlDays,
  messages: {
    between: t('frontend_settings.newly_detected_tokens.ttl_days.validation.invalid_range', {
      max: maxTtlDays,
      min: minTtlDays,
    }),
    required: t('frontend_settings.newly_detected_tokens.ttl_days.validation.non_empty'),
  },
  min: minTtlDays,
});
</script>

<template>
  <SettingNumber
    class="mt-1"
    setting="newlyDetectedTokensTtlDays"
    :schema="schema"
    :label="t('frontend_settings.newly_detected_tokens.ttl_days.label')"
    :hint="t('frontend_settings.newly_detected_tokens.ttl_days.hint')"
    :error-message="t('frontend_settings.newly_detected_tokens.ttl_days.validation.error')"
  />
</template>
