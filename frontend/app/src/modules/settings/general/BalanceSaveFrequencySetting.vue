<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import { Defaults } from '@/modules/core/common/defaults';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });

function successMessage(frequency: number): string {
  return t('general_settings.balance_frequency.validation.success', { frequency });
}
</script>

<template>
  <SettingNumber
    setting="balanceSaveFrequency"
    data-testid="balance-save-frequency-input"
    :label="t('general_settings.balance_frequency.label')"
    :min="1"
    :max="Constraints.MAX_HOURS_DELAY"
    :default="Defaults.BALANCE_SAVE_FREQUENCY"
    :error-message="t('general_settings.balance_frequency.validation.error')"
    :success-message="successMessage"
  />
</template>
