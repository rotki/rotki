<template>
  <settings-option
    #default="{ error, success, update }"
    setting="ethStakingTaxableAfterWithdrawalEnabled"
    :error-message="
      $tc(
        'account_settings.messages.eth_staking_taxable_after_withdrawal.error'
      )
    "
    :success-message="
      enabled =>
        enabled
          ? $tc(
              'account_settings.messages.eth_staking_taxable_after_withdrawal.enabled'
            )
          : $tc(
              'account_settings.messages.eth_staking_taxable_after_withdrawal.disabled'
            )
    "
  >
    <v-switch
      v-model="ethStakingTaxableAfterWithdrawalEnabled"
      class="accounting-settings__eth-staking-taxable-after-withdrawal"
      :success-messages="success"
      :error-messages="error"
      :label="
        $tc('accounting_settings.labels.eth_staking_taxable_after_withdrawal')
      "
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSettings } from '@/composables/settings';

const ethStakingTaxableAfterWithdrawalEnabled = ref(false);
const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(
    ethStakingTaxableAfterWithdrawalEnabled,
    settings.ethStakingTaxableAfterWithdrawalEnabled
  );
});
</script>
