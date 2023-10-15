<script setup lang="ts">
import { type XswapBalance } from '@rotki/common/lib/defi/xswap';
import { type LpType } from '@rotki/common/lib/defi';

const props = defineProps<{
  item: XswapBalance;
  lpType: LpType;
}>();
const { getPoolName } = useLiquidityPosition();

const assets = computed(() => props.item.assets.map(({ asset }) => asset));
</script>

<template>
  <LpPoolHeader>
    <template #icon>
      <LpPoolIcon :assets="assets" :type="lpType" />
    </template>
    <template #name>
      {{ getPoolName(lpType, assets) }}
    </template>
    <template #hash>
      <HashLink :text="item.address" />
    </template>
    <template #detail>
      <UniswapPoolDetails :balance="item" />
    </template>
  </LpPoolHeader>
</template>
