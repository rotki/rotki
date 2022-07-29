<template>
  <div class="accounting-settings mt-n8">
    <setting-category>
      <template #title>
        {{ $t('accounting_settings.title') }}
      </template>

      <crypto-to-crypto-trade-setting />
      <gas-cost-setting />
      <tax-free-setting />
      <account-asset-movements-setting />
      <calculate-past-cost-basis-setting />
      <eth-staking-taxable-after-withdrawal-setting />
      <cost-basis-method-setting />
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

      <pnl-csv-with-formulas-setting />
      <pnl-csv-summary-setting />
    </setting-category>
  </div>
</template>

<script setup lang="ts">
import AccountAssetMovementsSetting from '@/components/settings/accounting/AccountAssetMovementsSetting.vue';
import CalculatePastCostBasisSetting from '@/components/settings/accounting/CalculatePastCostBasisSetting.vue';
import CostBasisMethodSetting from '@/components/settings/accounting/CostBasisMethodSetting.vue';
import CryptoToCryptoTradeSetting from '@/components/settings/accounting/CryptoToCryptoTradeSetting.vue';
import EthStakingTaxableAfterWithdrawalSetting from '@/components/settings/accounting/EthStakingTaxableAfterWithdrawalSetting.vue';
import GasCostSetting from '@/components/settings/accounting/GasCostSetting.vue';
import LedgerActionSettings from '@/components/settings/accounting/LedgerActionSettings.vue';
import PnlCsvSummarySetting from '@/components/settings/accounting/PnlCsvSummarySetting.vue';
import PnlCsvWithFormulasSetting from '@/components/settings/accounting/PnlCsvWithFormulasSetting.vue';
import TaxFreeSetting from '@/components/settings/accounting/TaxFreeSetting.vue';
import IgnoreAssetSetting from '@/components/settings/controls/IgnoreAssetSetting.vue';
import UnignoreAssetSetting from '@/components/settings/controls/UnignoreAssetSetting.vue';
import UpdateIgnoredAssetsSetting from '@/components/settings/controls/UpdateIgnoredAssetsSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
</script>
