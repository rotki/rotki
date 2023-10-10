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
    <TaxFreeSetting />
    <AccountAssetMovementsSetting />
    <CalculatePastCostBasisSetting />
    <EthStakingTaxableAfterWithdrawalSetting />
    <CostBasisMethodSetting />
  </SettingCategory>
</template>
