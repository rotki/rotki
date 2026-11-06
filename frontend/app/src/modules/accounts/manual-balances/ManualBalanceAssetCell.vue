<script setup lang="ts">
import ManualBalanceMissingAssetWarning from '@/modules/accounts/manual-balances/ManualBalanceMissingAssetWarning.vue';
import AssetDetails from '@/modules/assets/AssetDetails.vue';

/** A balance's asset, or a warning in its place when the asset is no longer known. */
const { asset, assetIsMissing = false } = defineProps<{
  asset: string;
  assetIsMissing?: boolean;
}>();
</script>

<template>
  <AssetDetails
    v-if="!assetIsMissing"
    class="[&>div]:max-w-48 xl:[&>div]:max-w-64 2xl:[&>div]:max-w-80"
    :asset="asset"
    :actions="{ hideActions: true }"
  />
  <ManualBalanceMissingAssetWarning v-else />
</template>
