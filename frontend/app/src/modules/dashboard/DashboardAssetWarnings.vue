<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { AssetDisplay } from '@/modules/assets/types';
import ManualBalanceMissingAssetWarning from '@/modules/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import AssetDetails from '@/modules/assets/AssetDetails.vue';

defineProps<{
  asset: AssetBalanceWithPrice;
  isAssetMissing: boolean;
}>();

const emit = defineEmits<{
  'missing-asset-click': [item: AssetBalanceWithPrice];
}>();

/** The dashboard rows are compact: a 28px icon in the small avatar box. */
const display: AssetDisplay = { dense: true, size: '28px' };

function onMissingAssetClick(item: AssetBalanceWithPrice): void {
  emit('missing-asset-click', item);
}
</script>

<template>
  <ManualBalanceMissingAssetWarning
    v-if="isAssetMissing"
    @click="onMissingAssetClick(asset)"
  />

  <div
    v-else
    class="[&_.text-caption]:!leading-4"
  >
    <AssetDetails
      :asset="asset.asset"
      :display="display"
      :resolution="{ isCollectionParent: !!asset.breakdown }"
    />
  </div>
</template>
