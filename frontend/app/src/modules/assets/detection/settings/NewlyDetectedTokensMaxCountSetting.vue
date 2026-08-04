<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import { numberSettingSchema } from '@/modules/settings/controls/setting-field-schemas';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const minCount = Constraints.NEWLY_DETECTED_TOKENS_MIN_COUNT;
const maxCountLimit = Constraints.NEWLY_DETECTED_TOKENS_MAX_COUNT;

const schema = numberSettingSchema({
  max: maxCountLimit,
  messages: {
    between: t('frontend_settings.newly_detected_tokens.max_count.validation.invalid_range', {
      max: maxCountLimit,
      min: minCount,
    }),
    required: t('frontend_settings.newly_detected_tokens.max_count.validation.non_empty'),
  },
  min: minCount,
});
</script>

<template>
  <SettingNumber
    class="mt-1"
    setting="newlyDetectedTokensMaxCount"
    :schema="schema"
    :label="t('frontend_settings.newly_detected_tokens.max_count.label')"
    :hint="t('frontend_settings.newly_detected_tokens.max_count.hint')"
    :error-message="t('frontend_settings.newly_detected_tokens.max_count.validation.error')"
  />
</template>
