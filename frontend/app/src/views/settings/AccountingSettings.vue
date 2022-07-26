<template>
  <div class="accounting-settings mt-n8">
    <setting-category>
      <template #title>
        {{ $t('accounting_settings.title') }}
      </template>

      <settings-option
        #default="{ error, success, update }"
        setting="includeCrypto2crypto"
        :error-message="$tc('account_settings.messages.crypto_to_crypto')"
      >
        <v-switch
          v-model="crypto2CryptoTrades"
          class="accounting-settings__crypto2crypto"
          :label="$tc('accounting_settings.labels.crypto_to_crypto')"
          color="primary"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="includeGasCosts"
        :error-message="$tc('account_settings.messages.gas_costs')"
      >
        <v-switch
          v-model="gasCosts"
          class="accounting-settings__include-gas-costs"
          :label="$tc('accounting_settings.labels.gas_costs')"
          :success-messages="success"
          :error-messages="error"
          color="primary"
          @change="update"
        />
      </settings-option>

      <tax-free-setting />

      <settings-option
        #default="{ error, success, update }"
        setting="accountForAssetsMovements"
        :error-message="
          $tc('account_settings.messages.account_for_assets_movements')
        "
      >
        <v-switch
          v-model="accountForAssetsMovements"
          class="accounting-settings__account-for-assets-movements"
          :success-messages="success"
          :error-messages="error"
          :label="
            $tc('accounting_settings.labels.account_for_assets_movements')
          "
          color="primary"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="calculatePastCostBasis"
        :error-message="$tc('account_settings.messages.cost_basis.error')"
        :success-message="
          enabled =>
            enabled
              ? $tc('account_settings.messages.cost_basis.enabled')
              : $tc('account_settings.messages.cost_basis.disabled')
        "
      >
        <v-switch
          v-model="calculatePastCostBasis"
          class="accounting-settings__past-cost-basis"
          :success-messages="success"
          :error-messages="error"
          :label="$tc('accounting_settings.labels.calculate_past_cost_basis')"
          color="primary"
          @change="update"
        />
      </settings-option>

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
            $tc(
              'accounting_settings.labels.eth_staking_taxable_after_withdrawal'
            )
          "
          color="primary"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="costBasisMethod"
        :success-message="
          method =>
            $tc('account_settings.messages.cost_basis_method.success', 0, {
              method: method.toUpperCase()
            })
        "
        :error-message="
          method =>
            $tc('account_settings.messages.cost_basis_method.error', 0, {
              method: method.toUpperCase()
            })
        "
      >
        <cost-basis-method-settings
          v-model="costBasisMethod"
          class="accounting-settings__cost-basis-method pt-4"
          :success-messages="success"
          :error-messages="error"
          :label="$t('accounting_settings.labels.cost_basis_method')"
          color="primary"
          @change="update"
        />
      </settings-option>
    </setting-category>
    <setting-category>
      <template #title>
        {{ $t('account_settings.asset_settings.title') }}
      </template>

      <ignore-asset-setting />
      <unignore-asset-setting />
      <update-ignored-assets-setting />
    </setting-category>
    <ledger-action-settings />
    <setting-category>
      <template #title>
        {{ $t('account_settings.csv_export_settings.title') }}
      </template>

      <settings-option
        #default="{ error, success, update }"
        setting="pnlCsvWithFormulas"
        :error-message="$tc('account_settings.messages.export_csv_formulas')"
      >
        <v-switch
          v-model="exportCSVFormulas"
          class="csv_export_settings__exportCSVFormulas"
          :label="
            $tc(
              'account_settings.csv_export_settings.labels.export_csv_formulas'
            )
          "
          color="primary"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="pnlCsvHaveSummary"
        :error-message="$tc('account_settings.messages.have_csv_summary')"
      >
        <v-switch
          v-model="haveCSVSummary"
          class="csv_export_settings__haveCSVSummary"
          :label="
            $tc('account_settings.csv_export_settings.labels.have_csv_summary')
          "
          color="primary"
          :success-messages="success"
          :error-messages="error"
          @change="update"
        />
      </settings-option>
    </setting-category>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import CostBasisMethodSettings from '@/components/settings/accounting/CostBasisMethodSettings.vue';
import LedgerActionSettings from '@/components/settings/accounting/LedgerActionSettings.vue';
import IgnoreAssetSetting from '@/components/settings/controls/IgnoreAssetSetting.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import UnignoreAssetSetting from '@/components/settings/controls/UnignoreAssetSetting.vue';
import UpdateIgnoredAssetsSetting from '@/components/settings/controls/UpdateIgnoredAssetsSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { useSettings } from '@/composables/settings';
import { CostBasisMethod } from '@/types/user';

const haveCSVSummary = ref(false);
const exportCSVFormulas = ref(false);
const crypto2CryptoTrades = ref(false);
const gasCosts = ref(false);
const accountForAssetsMovements = ref(false);
const calculatePastCostBasis = ref(false);
const ethStakingTaxableAfterWithdrawalEnabled = ref(false);
const costBasisMethod = ref<CostBasisMethod>(CostBasisMethod.Fifo);

const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(haveCSVSummary, settings.pnlCsvHaveSummary);
  set(exportCSVFormulas, settings.pnlCsvWithFormulas);
  set(crypto2CryptoTrades, settings.includeCrypto2crypto);
  set(gasCosts, settings.includeGasCosts);
  set(accountForAssetsMovements, settings.accountForAssetsMovements);
  set(calculatePastCostBasis, settings.calculatePastCostBasis);
  set(
    ethStakingTaxableAfterWithdrawalEnabled,
    settings.ethStakingTaxableAfterWithdrawalEnabled
  );
  set(costBasisMethod, settings.costBasisMethod);
});
</script>
