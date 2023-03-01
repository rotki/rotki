<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="accounting-settings mt-n8">
    <setting-category>
      <template #title>
        {{ t('accounting_settings.title') }}
      </template>

      <crypto-to-crypto-trade-setting />
      <gas-cost-setting />
      <tax-free-setting />
      <account-asset-movements-setting />
      <calculate-past-cost-basis-setting />
      <eth-staking-taxable-after-withdrawal-setting />
      <cost-basis-method-setting />
    </setting-category>
    <ledger-action-settings />
    <setting-category>
      <template #title>
        {{ t('account_settings.csv_export_settings.title') }}
      </template>

      <pnl-csv-with-formulas-setting />
      <pnl-csv-summary-setting />
    </setting-category>
  </div>
</template>
