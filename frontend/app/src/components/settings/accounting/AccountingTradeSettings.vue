<script setup lang="ts">
import CalculatePastCostBasisSetting from '@/components/settings/accounting/CalculatePastCostBasisSetting.vue';
import CostBasisFeesSetting from '@/components/settings/accounting/CostBasisFeesSetting.vue';
import CostBasisMethodSetting from '@/components/settings/accounting/CostBasisMethodSetting.vue';
import CryptoToCryptoTradeSetting from '@/components/settings/accounting/CryptoToCryptoTradeSetting.vue';
import EthStakingTaxableAfterWithdrawalSetting from '@/components/settings/accounting/EthStakingTaxableAfterWithdrawalSetting.vue';
import GasCostSetting from '@/components/settings/accounting/GasCostSetting.vue';
import TaxFreeSetting from '@/components/settings/accounting/TaxFreeSetting.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';

const { t } = useI18n();
</script>

<template>
  <SettingsItem class="border-t mt-6">
    <template #title>
      {{ t('accounting_settings.trade.title') }}
    </template>
    <div class="pl-4 md:pl-8 lg:pl-12">
      <CryptoToCryptoTradeSetting />
      <GasCostSetting />
      <TaxFreeSetting />
      <CalculatePastCostBasisSetting />
      <CostBasisFeesSetting />
      <CostBasisMethodSetting />
      <EthStakingTaxableAfterWithdrawalSetting />
    </div>
  </SettingsItem>
</template>
