<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="includeGasCosts"
    data-testid="include-gas-costs-switch"
    :debounce="1500"
    :label="t('accounting_settings.trade.labels.include_gas_costs')"
    :error-message="t('account_settings.messages.gas_costs')"
  />
</template>
