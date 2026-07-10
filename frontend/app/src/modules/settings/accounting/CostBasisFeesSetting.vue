<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });

function getSuccessMessage(enabled: boolean): string {
  return enabled
    ? t('account_settings.messages.include_fees_in_cost_basis.enabled')
    : t('account_settings.messages.include_fees_in_cost_basis.disabled');
}
</script>

<template>
  <SettingSwitch
    setting="includeFeesInCostBasis"
    data-testid="include-fees-in-cost-basis-switch"
    :debounce="1500"
    :label="t('accounting_settings.trade.labels.include_fees_in_cost_basis')"
    :error-message="t('account_settings.messages.include_fees_in_cost_basis.error')"
    :success-message="getSuccessMessage"
  />
</template>
