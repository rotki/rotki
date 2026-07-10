<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });

function getSuccessMessage(enabled: boolean): string {
  return enabled
    ? t('account_settings.messages.eth_staking_taxable_after_withdrawal.enabled')
    : t('account_settings.messages.eth_staking_taxable_after_withdrawal.disabled');
}
</script>

<template>
  <SettingSwitch
    setting="ethStakingTaxableAfterWithdrawalEnabled"
    :debounce="1500"
    :label="t('accounting_settings.trade.labels.eth_staking_taxable_after_withdrawal_enabled')"
    :error-message="t('account_settings.messages.eth_staking_taxable_after_withdrawal.error')"
    :success-message="getSuccessMessage"
  />
</template>
