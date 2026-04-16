<script setup lang="ts">
import { getAddressFromEvmIdentifier } from '@rotki/common';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetPageNavigation } from '@/modules/assets/use-asset-page-navigation';
import HashLink from '@/modules/shell/components/HashLink.vue';

const { asset, link = false } = defineProps<{
  asset: string;
  link?: boolean;
}>();

defineSlots<{
  default: () => any;
}>();

const address = reactify(getAddressFromEvmIdentifier)(() => asset);
const { useAssetInfo } = useAssetInfoRetrieval();
const assetDetails = useAssetInfo(() => asset);
const { navigateToDetails } = useAssetPageNavigation(() => asset);
</script>

<template>
  <div class="flex flex-row gap-1">
    <RuiButton
      size="sm"
      icon
      variant="text"
      @click="navigateToDetails()"
    >
      <slot />
    </RuiButton>
    <HashLink
      v-if="address && link"
      display-mode="link"
      hide-text
      type="token"
      :text="address"
      :location="assetDetails?.evmChain"
    />
  </div>
</template>
