<script setup lang="ts">
import { getAddressFromEvmIdentifier } from '@rotki/common';
import { useAssetPageNavigation } from '@/composables/assets/navigation';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import HashLink from '@/modules/common/links/HashLink.vue';

const { asset, link = false } = defineProps<{
  asset: string;
  link?: boolean;
}>();

defineSlots<{
  default: () => any;
}>();

const address = reactify(getAddressFromEvmIdentifier)(() => asset);
const { assetInfo } = useAssetInfoRetrieval();
const assetDetails = assetInfo(() => asset);
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
