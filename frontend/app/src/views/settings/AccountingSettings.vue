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

      <settings-option
        #default="{ error, success, update }"
        setting="taxfreeAfterPeriod"
        :transform="getTaxFreePeriod"
        :success-message="
          enabled =>
            $tc('account_settings.messages.tax_free', 0, {
              enabled: enabled ? 'enabled' : 'disabled'
            })
        "
        @finished="resetTaxFreePeriod"
      >
        <v-switch
          v-model="taxFreePeriod"
          class="accounting-settings__taxfree-period"
          :success-messages="success"
          :error-messages="error"
          :label="$tc('accounting_settings.labels.tax_free')"
          color="primary"
          @change="update"
        />
      </settings-option>

      <settings-option
        #default="{ error, success, update }"
        setting="taxfreeAfterPeriod"
        :transform="value => (value ? convertPeriod(value, 'days') : -1)"
        :rules="taxFreeRules"
        :success-message="
          period =>
            $tc('account_settings.messages.tax_free_period', 0, {
              period
            })
        "
        @finished="resetTaxFreePeriod"
      >
        <v-text-field
          v-model="taxFreeAfterPeriod"
          outlined
          class="accounting-settings__taxfree-period-days pt-4"
          :success-messages="success"
          :error-messages="error"
          :disabled="!taxFreePeriod"
          :rules="taxFreeRules"
          :label="$tc('accounting_settings.labels.tax_free_period')"
          type="number"
          @change="update"
        />
      </settings-option>

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
import i18n from '@/i18n';
import { CostBasisMethod } from '@/types/user';

const haveCSVSummary = ref(false);
const exportCSVFormulas = ref(false);
const crypto2CryptoTrades = ref(false);
const gasCosts = ref(false);
const taxFreeAfterPeriod = ref<number | null>(null);
const taxFreePeriod = ref(false);
const accountForAssetsMovements = ref(false);
const calculatePastCostBasis = ref(false);
const ethStakingTaxableAfterWithdrawalEnabled = ref(false);
const costBasisMethod = ref<CostBasisMethod>(CostBasisMethod.Fifo);

const taxFreeRules = [
  (v: string) =>
    !!v ||
    !get(taxFreeAfterPeriod) ||
    i18n.tc('account_settings.validation.tax_free_days'),
  (v: string) =>
    (v && parseInt(v) > 0) ||
    !get(taxFreeAfterPeriod) ||
    i18n.tc('account_settings.validation.tax_free_days_gt_zero')
];

const { accountingSettings } = useSettings();

const resetTaxFreePeriod = () => {
  const settings = get(accountingSettings);
  const period = settings.taxfreeAfterPeriod;

  if (period && period > -1) {
    set(taxFreePeriod, true);
    set(taxFreeAfterPeriod, convertPeriod(period, 'seconds'));
  } else {
    set(taxFreePeriod, false);
    set(taxFreeAfterPeriod, null);
  }
};

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

  resetTaxFreePeriod();
});

const convertPeriod = (period: number, currentType: 'days' | 'seconds') => {
  const dayInSeconds = 86400;
  if (currentType === 'days') {
    return period * dayInSeconds;
  } else if (currentType === 'seconds') {
    return period / dayInSeconds;
  }
  throw new Error(`invalid type: ${currentType}`);
};

const getTaxFreePeriod = (enabled: boolean) => {
  if (!enabled) {
    return -1;
  }

  return convertPeriod(365, 'days');
};
</script>
