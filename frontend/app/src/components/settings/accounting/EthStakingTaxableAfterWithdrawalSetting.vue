<script setup lang="ts">
const ethStakingTaxableAfterWithdrawalEnabled = ref(false);
const { ethStakingTaxableAfterWithdrawalEnabled: enabled } = storeToRefs(
  useAccountingSettingsStore()
);

onMounted(() => {
  set(ethStakingTaxableAfterWithdrawalEnabled, get(enabled));
});

const { t } = useI18n();

const getSuccessMessage = (enabled: boolean) =>
  enabled
    ? t(
        'account_settings.messages.eth_staking_taxable_after_withdrawal.enabled'
      )
    : t(
        'account_settings.messages.eth_staking_taxable_after_withdrawal.disabled'
      );
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="ethStakingTaxableAfterWithdrawalEnabled"
    :error-message="
      t('account_settings.messages.eth_staking_taxable_after_withdrawal.error')
    "
    :success-message="getSuccessMessage"
  >
    <v-switch
      v-model="ethStakingTaxableAfterWithdrawalEnabled"
      class="accounting-settings__eth-staking-taxable-after-withdrawal"
      :success-messages="success"
      :error-messages="error"
      :label="
        t('accounting_settings.labels.eth_staking_taxable_after_withdrawal')
      "
      color="primary"
      @change="update($event)"
    />
  </settings-option>
</template>
