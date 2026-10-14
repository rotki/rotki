<script setup lang="ts">
import CryptoToCryptoTradeSetting from '@/modules/settings/accounting/CryptoToCryptoTradeSetting.vue';
import EthStakingTaxableAfterWithdrawalSetting from '@/modules/settings/accounting/EthStakingTaxableAfterWithdrawalSetting.vue';
import GasCostSetting from '@/modules/settings/accounting/GasCostSetting.vue';
import TaxFreeSetting from '@/modules/settings/accounting/TaxFreeSetting.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('accounting_settings.taxes.title') }}
    </template>
    <SettingsItem setting-key="includeCrypto2crypto">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.include_crypto2crypto') }}
      </template>
      <CryptoToCryptoTradeSetting />
    </SettingsItem>
    <SettingsItem setting-key="includeGasCosts">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.include_gas_costs') }}
      </template>
      <GasCostSetting />
    </SettingsItem>
    <SettingsItem setting-key="taxfreeAfterPeriod">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.tax_free') }}
      </template>
      <TaxFreeSetting />
    </SettingsItem>
    <SettingsItem setting-key="ethStakingTaxableAfterWithdrawalEnabled">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.eth_staking_taxable_after_withdrawal_enabled') }}
      </template>
      <EthStakingTaxableAfterWithdrawalSetting />
    </SettingsItem>
  </SettingCategory>
</template>
