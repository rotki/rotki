<script setup lang="ts">
import HashLink from '@/components/helper/HashLink.vue';
import { useAssetPageNavigation } from '@/composables/assets/navigation';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { getAddressFromEvmIdentifier } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    asset: string;
    link?: boolean;
  }>(),
  {
    link: false,
  },
);

defineSlots<{
  default: () => any;
}>();

const { asset } = toRefs(props);
const address = reactify(getAddressFromEvmIdentifier)(asset);
const { assetInfo } = useAssetInfoRetrieval();
const assetDetails = assetInfo(asset);
const { navigateToDetails } = useAssetPageNavigation(asset);
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
      link-only
      type="token"
      :text="address"
      :evm-chain="assetDetails?.evmChain"
    />
  </div>
</template>
