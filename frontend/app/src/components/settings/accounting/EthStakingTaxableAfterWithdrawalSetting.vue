<script setup lang="ts">
const ethStakingTaxableAfterWithdrawalEnabled = ref(false);
const { ethStakingTaxableAfterWithdrawalEnabled: enabled } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(ethStakingTaxableAfterWithdrawalEnabled, get(enabled));
});

const { t } = useI18n();

function getSuccessMessage(enabled: boolean) {
  return enabled
    ? t('account_settings.messages.eth_staking_taxable_after_withdrawal.enabled')
    : t('account_settings.messages.eth_staking_taxable_after_withdrawal.disabled');
}
</script>

<template>
  <SettingsOption
    setting="ethStakingTaxableAfterWithdrawalEnabled"
    :error-message="t('account_settings.messages.eth_staking_taxable_after_withdrawal.error')"
    :success-message="getSuccessMessage"
  >
    <template #title>
      {{ t('accounting_settings.trade.titles.eth_staking') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiSwitch
        v-model="ethStakingTaxableAfterWithdrawalEnabled"
        class="accounting-settings__eth-staking-taxable-after-withdrawal"
        :success-messages="success"
        :error-messages="error"
        :label="t('accounting_settings.trade.labels.eth_staking_taxable_after_withdrawal_enabled')"
        color="primary"
        @update:model-value="update($event)"
      />
    </template>
  </SettingsOption>
</template>
