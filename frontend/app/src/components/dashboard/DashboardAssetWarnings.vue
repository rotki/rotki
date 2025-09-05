<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import ManualBalanceMissingAssetWarning from '@/components/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';

defineProps<{
  asset: AssetBalanceWithPrice;
  isAssetMissing: boolean;
}>();

const emit = defineEmits<{
  'missing-asset-click': [item: AssetBalanceWithPrice];
}>();

function onMissingAssetClick(item: AssetBalanceWithPrice): void {
  emit('missing-asset-click', item);
}
</script>

<template>
  <ManualBalanceMissingAssetWarning
    v-if="isAssetMissing"
    @click="onMissingAssetClick(asset)"
  />

  <AssetDetails
    v-else
    :asset="asset.asset"
    :is-collection-parent="!!asset.breakdown"
  />
</template>
