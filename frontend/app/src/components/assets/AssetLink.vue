<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    asset: string;
    icon?: boolean;
    text?: boolean;
    link?: boolean;
  }>(),
  {
    icon: false,
    text: false,
    link: false
  }
);

const { asset } = toRefs(props);
const address = reactify(getAddressFromEvmIdentifier)(asset);
const { assetInfo } = useAssetInfoRetrieval();
const assetDetails = assetInfo(asset);
const { navigateToDetails } = useAssetPageNavigation(asset);
</script>

<template>
  <div class="flex flex-row">
    <VBtn :icon="icon" :text="text" @click="navigateToDetails()">
      <slot />
    </VBtn>
    <HashLink
      v-if="address && link"
      link-only
      type="address"
      :text="address"
      :evm-chain="assetDetails?.evmChain"
    />
  </div>
</template>
