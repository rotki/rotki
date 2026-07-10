<script setup lang="ts">
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/modules/core/common/constraints';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const minCount = Constraints.NEWLY_DETECTED_TOKENS_MIN_COUNT;
const maxCountLimit = Constraints.NEWLY_DETECTED_TOKENS_MAX_COUNT;

const rules = {
  value: {
    between: helpers.withMessage(
      t('frontend_settings.newly_detected_tokens.max_count.validation.invalid_range', {
        max: maxCountLimit,
        min: minCount,
      }),
      between(minCount, maxCountLimit),
    ),
    required: helpers.withMessage(t('frontend_settings.newly_detected_tokens.max_count.validation.non_empty'), required),
  },
};
</script>

<template>
  <SettingNumber
    class="mt-1"
    setting="newlyDetectedTokensMaxCount"
    :rules="rules"
    :label="t('frontend_settings.newly_detected_tokens.max_count.label')"
    :hint="t('frontend_settings.newly_detected_tokens.max_count.hint')"
    :error-message="t('frontend_settings.newly_detected_tokens.max_count.validation.error')"
  />
</template>
