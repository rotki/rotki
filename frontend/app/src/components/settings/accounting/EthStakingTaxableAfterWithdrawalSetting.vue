<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

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
    #default="{ error, success, update }"
    setting="ethStakingTaxableAfterWithdrawalEnabled"
    :error-message="t('account_settings.messages.eth_staking_taxable_after_withdrawal.error')"
    :success-message="getSuccessMessage"
  >
    <RuiSwitch
      v-model="ethStakingTaxableAfterWithdrawalEnabled"
      :success-messages="success"
      :error-messages="error"
      :label="t('accounting_settings.trade.labels.eth_staking_taxable_after_withdrawal_enabled')"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
