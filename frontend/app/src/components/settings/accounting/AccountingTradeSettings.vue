<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('accounting_settings.trade.title') }}
    </template>
    <div class="pl-4 md:pl-8 lg:pl-12">
      <CryptoToCryptoTradeSetting />
      <GasCostSetting />
      <TaxFreeSetting />
      <AccountAssetMovementsSetting />
      <CalculatePastCostBasisSetting />
      <CostBasisFeesSetting />
      <CostBasisMethodSetting />
      <EthStakingTaxableAfterWithdrawalSetting />
    </div>
  </SettingsItem>
</template>
