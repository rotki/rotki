<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const useAssetCollectionsInCostBasis = ref<boolean>(true);
const { useAssetCollectionsInCostBasis: enabled } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(useAssetCollectionsInCostBasis, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });

function getSuccessMessage(enabled: boolean): string {
  return enabled
    ? t('account_settings.messages.use_asset_collections_in_cost_basis.enabled')
    : t('account_settings.messages.use_asset_collections_in_cost_basis.disabled');
}
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="useAssetCollectionsInCostBasis"
    :error-message="t('account_settings.messages.use_asset_collections_in_cost_basis.error')"
    :success-message="getSuccessMessage"
  >
    <RuiSwitch
      v-model="useAssetCollectionsInCostBasis"
      data-cy="use-asset-collections-in-cost-basis-switch"
      :success-messages="success"
      :error-messages="error"
      :label="t('accounting_settings.trade.labels.use_asset_collections_in_cost_basis')"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
