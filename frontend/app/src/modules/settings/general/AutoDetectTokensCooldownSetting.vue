<script setup lang="ts">
import { between, helpers, required } from '@vuelidate/validators';
import { Constraints } from '@/modules/core/common/constraints';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const minHours = Constraints.AUTO_DETECT_TOKENS_COOLDOWN_MIN_HOURS;
const maxHours = Constraints.AUTO_DETECT_TOKENS_COOLDOWN_MAX_HOURS;

const rules = {
  value: {
    between: helpers.withMessage(
      t('general_settings.auto_detect_tokens_cooldown.validation.invalid_value', {
        end: maxHours,
        start: minHours,
      }),
      between(minHours, maxHours),
    ),
    required: helpers.withMessage(t('general_settings.auto_detect_tokens_cooldown.validation.non_empty'), required),
  },
};
</script>

<template>
  <SettingNumber
    setting="autoDetectTokensCooldownHours"
    class="w-full"
    data-testid="auto-detect-tokens-cooldown-input"
    :rules="rules"
    :label="t('general_settings.auto_detect_tokens_cooldown.label')"
    :error-message="t('general_settings.auto_detect_tokens_cooldown.validation.error')"
    :success-message="t('general_settings.auto_detect_tokens_cooldown.validation.success')"
  />
</template>
