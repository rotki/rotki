<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });

function getSuccessMessage(enabled: boolean): string {
  return enabled
    ? t('account_settings.messages.use_asset_collections_in_cost_basis.enabled')
    : t('account_settings.messages.use_asset_collections_in_cost_basis.disabled');
}
</script>

<template>
  <SettingSwitch
    setting="useAssetCollectionsInCostBasis"
    data-cy="use-asset-collections-in-cost-basis-switch"
    :debounce="1500"
    :label="t('accounting_settings.trade.labels.use_asset_collections_in_cost_basis')"
    :error-message="t('account_settings.messages.use_asset_collections_in_cost_basis.error')"
    :success-message="getSuccessMessage"
  />
</template>
