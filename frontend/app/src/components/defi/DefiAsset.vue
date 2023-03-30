<script setup lang="ts">
import { type ComputedRef, type PropType } from 'vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import { type DefiAsset } from '@/types/defi/overview';
import { createEvmIdentifierFromAddress } from '@/utils/assets';

const props = defineProps({
  asset: { required: true, type: Object as PropType<DefiAsset> }
});

const { asset } = toRefs(props);

const evmIdentifier: ComputedRef<string> = computed(() =>
  createEvmIdentifierFromAddress(get(asset).tokenAddress)
);
</script>
<template>
  <div class="defi-asset d-flex flex-row align-center py-4">
    <asset-icon size="32px" :identifier="evmIdentifier" />
    <span class="ml-3">{{ asset.tokenSymbol }}</span>
    <v-spacer />
    <div class="d-flex flex-column align-end">
      <balance-display no-icon :asset="evmIdentifier" :value="asset.balance" />
    </div>
  </div>
</template>
