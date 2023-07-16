<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <div class="accounting-settings mt-n8">
    <SettingCategory>
      <template #title>
        {{ t('accounting_settings.title') }}
      </template>

      <CryptoToCryptoTradeSetting />
      <GasCostSetting />
      <TaxFreeSetting />
      <AccountAssetMovementsSetting />
      <CalculatePastCostBasisSetting />
      <EthStakingTaxableAfterWithdrawalSetting />
      <CostBasisMethodSetting />
    </SettingCategory>
    <LedgerActionSettings />
    <SettingCategory>
      <template #title>
        {{ t('account_settings.csv_export_settings.title') }}
      </template>

      <PnlCsvWithFormulasSetting />
      <PnlCsvSummarySetting />
    </SettingCategory>
  </div>
</template>
