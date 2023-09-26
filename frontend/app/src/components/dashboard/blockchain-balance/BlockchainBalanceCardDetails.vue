<script setup lang="ts">
import { type SubBlockchainTotal } from '@/types/blockchain';
import { type ActionDataEntry } from '@/types/action';

withDefaults(
  defineProps<{
    child: SubBlockchainTotal;
    details: ActionDataEntry | null;
  }>(),
  {
    details: null
  }
);

const css = useCssModule();
</script>

<template>
  <VListItem
    v-if="details"
    :id="`${child.protocol}_box`"
    :key="child.protocol"
    class="blockchain-balance-box__item sub-item min-h-[2.25rem] group"
    :to="details.detailPath"
    :class="css['sub-item']"
  >
    <VListItemAvatar
      tile
      class="grayscale group-hover:grayscale-0 m-0 mr-1 ml-10"
    >
      <AdaptiveWrapper>
        <VImg :src="details.icon" width="24px" height="24px" />
      </AdaptiveWrapper>
    </VListItemAvatar>
    <VListItemContent>
      <div class="flex flex-wrap justify-between gap-2">
        <span>
          {{ details.label }}
        </span>
        <AmountDisplay
          show-currency="symbol"
          fiat-currency="USD"
          :value="child.usdValue"
          :loading="child.loading"
        />
      </div>
    </VListItemContent>
  </VListItem>
</template>

<style module lang="scss">
.sub-item {
  &:after {
    @apply absolute opacity-50 border-rui-text-secondary border-b border-l;
    @apply w-4 min-h-[1rem] h-[40%] top-[10%] left-[2.2rem];
  }
}
</style>
