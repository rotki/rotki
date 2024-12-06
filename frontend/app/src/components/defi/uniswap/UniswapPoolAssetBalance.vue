<script lang="ts" setup>
import { useRefMap } from '@/composables/utils/useRefMap';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import HashLink from '@/components/helper/HashLink.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import type { XswapAsset } from '@rotki/common';

const props = defineProps<{ asset: XswapAsset }>();

const { tokenAddress } = useAssetInfoRetrieval();
const address = tokenAddress(useRefMap(toRef(props, 'asset'), x => x.asset));
</script>

<template>
  <div class="flex items-center gap-4">
    <AssetIcon
      :identifier="asset.asset"
      size="32px"
    />
    <BalanceDisplay
      no-icon
      align="start"
      :asset="asset.asset"
      :value="asset.userBalance"
    />
    <HashLink
      link-only
      :text="address"
    />
  </div>
</template>
