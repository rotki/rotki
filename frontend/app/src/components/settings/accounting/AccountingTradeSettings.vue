<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('accounting_settings.trade.title') }}
    </template>

    <CryptoToCryptoTradeSetting />
    <GasCostSetting />

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.tax_free') }}
      </template>
      <TaxFreeSetting />
    </SettingsItem>

    <AccountAssetMovementsSetting />

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.cost_basis') }}
      </template>
      <CalculatePastCostBasisSetting />
      <CostBasisFeesSetting />
      <CostBasisMethodSetting />
    </SettingsItem>

    <EthStakingTaxableAfterWithdrawalSetting />
  </SettingCategory>
</template>
