<script setup lang="ts">
import CalculatePastCostBasisSetting from '@/modules/settings/accounting/CalculatePastCostBasisSetting.vue';
import CostBasisFeesSetting from '@/modules/settings/accounting/CostBasisFeesSetting.vue';
import CostBasisMethodSetting from '@/modules/settings/accounting/CostBasisMethodSetting.vue';
import UseAssetCollectionsInCostBasisSetting from '@/modules/settings/accounting/UseAssetCollectionsInCostBasisSetting.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('accounting_settings.cost_basis.title') }}
    </template>
    <SettingsItem setting-key="costBasisMethod">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.cost_basis_method') }}
      </template>
      <CostBasisMethodSetting />
    </SettingsItem>
    <SettingsItem setting-key="calculatePastCostBasis">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.calculate_past_cost_basis') }}
      </template>
      <CalculatePastCostBasisSetting />
    </SettingsItem>
    <SettingsItem setting-key="includeFeesInCostBasis">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.include_fees_in_cost_basis') }}
      </template>
      <CostBasisFeesSetting />
    </SettingsItem>
    <SettingsItem setting-key="useAssetCollectionsInCostBasis">
      <template #subtitle>
        {{ t('accounting_settings.trade.descriptions.use_asset_collections_in_cost_basis') }}
      </template>
      <UseAssetCollectionsInCostBasisSetting />
    </SettingsItem>
  </SettingCategory>
</template>
