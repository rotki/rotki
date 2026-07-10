<script setup lang="ts">
import { helpers, required } from '@vuelidate/validators';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const rules = {
  value: {
    required: helpers.withMessage(t('general_settings.validation.floating_precision.non_empty'), required),
  },
};

function errorMessage(precision: number): string {
  return t('general_settings.validation.floating_precision.error', { precision });
}

function successMessage(precision: number): string {
  return t('general_settings.validation.floating_precision.success', { precision });
}
</script>

<template>
  <SettingNumber
    setting="floatingPrecision"
    data-testid="floating-precision-settings"
    :rules="rules"
    :label="t('general_settings.amount.labels.floating_precision')"
    :error-message="errorMessage"
    :success-message="successMessage"
  />
</template>
