<script setup lang="ts">
import CalculatePastCostBasisSetting from '@/modules/settings/accounting/CalculatePastCostBasisSetting.vue';
import CostBasisFeesSetting from '@/modules/settings/accounting/CostBasisFeesSetting.vue';
import CostBasisMethodSetting from '@/modules/settings/accounting/CostBasisMethodSetting.vue';
import CryptoToCryptoTradeSetting from '@/modules/settings/accounting/CryptoToCryptoTradeSetting.vue';
import EthStakingTaxableAfterWithdrawalSetting from '@/modules/settings/accounting/EthStakingTaxableAfterWithdrawalSetting.vue';
import GasCostSetting from '@/modules/settings/accounting/GasCostSetting.vue';
import TaxFreeSetting from '@/modules/settings/accounting/TaxFreeSetting.vue';
import UseAssetCollectionsInCostBasisSetting from '@/modules/settings/accounting/UseAssetCollectionsInCostBasisSetting.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem
    :id="SettingsHighlightIds.ACCOUNTING_TRADE"
    class="border-t mt-6"
  >
    <template #title>
      {{ t('accounting_settings.trade.title') }}
    </template>
    <div class="pl-4 md:pl-8 lg:pl-12">
      <CryptoToCryptoTradeSetting />
      <GasCostSetting />
      <TaxFreeSetting />
      <CalculatePastCostBasisSetting />
      <CostBasisFeesSetting />
      <UseAssetCollectionsInCostBasisSetting />
      <CostBasisMethodSetting />
      <EthStakingTaxableAfterWithdrawalSetting />
    </div>
  </SettingsItem>
</template>
