<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });

function switchSuccessMessage(enabled: boolean): string {
  return enabled
    ? t('account_settings.messages.cost_basis.enabled')
    : t('account_settings.messages.cost_basis.disabled');
}
</script>

<template>
  <SettingSwitch
    setting="calculatePastCostBasis"
    :debounce="1500"
    :label="t('accounting_settings.trade.labels.calculate_past_cost_basis')"
    :error-message="t('account_settings.messages.cost_basis.error')"
    :success-message="switchSuccessMessage"
  />
</template>
