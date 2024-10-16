<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('accounting_settings.trade.title') }}
    </template>

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.crypto2crypto') }}
      </template>
      <CryptoToCryptoTradeSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.gas_costs') }}
      </template>
      <GasCostSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.tax_free') }}
      </template>
      <TaxFreeSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.assets_movements') }}
      </template>
      <AccountAssetMovementsSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.cost_basis') }}
      </template>
      <CalculatePastCostBasisSetting />
      <CostBasisFeesSetting />
      <CostBasisMethodSetting />
    </SettingsItem>

    <SettingsItem>
      <template #title>
        {{ t('accounting_settings.trade.titles.eth_staking') }}
      </template>
      <EthStakingTaxableAfterWithdrawalSetting />
    </SettingsItem>
  </SettingCategory>
</template>
