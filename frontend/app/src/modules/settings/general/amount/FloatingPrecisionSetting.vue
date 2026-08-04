<script setup lang="ts">
import { numberSettingSchema } from '@/modules/settings/controls/setting-field-schemas';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

const schema = numberSettingSchema({
  messages: { required: t('general_settings.validation.floating_precision.non_empty') },
});

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
    :schema="schema"
    :label="t('general_settings.amount.labels.floating_precision')"
    :error-message="errorMessage"
    :success-message="successMessage"
  />
</template>
