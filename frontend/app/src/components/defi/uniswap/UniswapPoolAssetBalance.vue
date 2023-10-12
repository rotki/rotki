<script lang="ts" setup>
import { type XswapAsset } from '@rotki/common/lib/defi/xswap';

const props = defineProps<{ asset: XswapAsset }>();

const { tokenAddress } = useAssetInfoRetrieval();
const address = tokenAddress(useRefMap(toRef(props, 'asset'), x => x.asset));
</script>

<template>
  <div class="flex flex-row items-center justify-between gap-4">
    <AssetIcon :identifier="asset.asset" size="32px" />
    <div class="flex flex-row gap-4">
      <BalanceDisplay
        no-icon
        align="start"
        :asset="asset.asset"
        :value="asset.userBalance"
      />
      <HashLink link-only :text="address" />
    </div>
  </div>
</template>
