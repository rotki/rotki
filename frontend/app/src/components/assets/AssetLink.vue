<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    asset: string;
    link?: boolean;
  }>(),
  {
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
  <div class="flex flex-row gap-1">
    <RuiButton size="sm" icon variant="text" @click="navigateToDetails()">
      <slot />
    </RuiButton>
    <HashLink
      v-if="address && link"
      link-only
      type="address"
      :text="address"
      :evm-chain="assetDetails?.evmChain"
    />
  </div>
</template>
