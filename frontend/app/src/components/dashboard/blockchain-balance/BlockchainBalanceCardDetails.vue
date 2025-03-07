<script setup lang="ts">
import type { ActionDataEntry } from '@/types/action';
import type { SubBlockchainTotal } from '@/types/blockchain';
import AppImage from '@/components/common/AppImage.vue';
import ListItem from '@/components/common/ListItem.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';

defineProps<{
  child: SubBlockchainTotal;
  details: ActionDataEntry | null;
}>();
</script>

<template>
  <RouterLink
    v-if="details"
    :to="details.detailPath || ''"
  >
    <ListItem
      :id="`${child.protocol}_box`"
      :key="child.protocol"
      class="blockchain-balance-box__item group py-1 pr-6"
      :class="$style['sub-item']"
    >
      <template #avatar>
        <div class="grayscale group-hover:grayscale-0">
          <AdaptiveWrapper>
            <AppImage
              :src="details.icon"
              width="24px"
              height="24px"
            />
          </AdaptiveWrapper>
        </div>
      </template>
      <div class="flex flex-wrap justify-between gap-1 text-rui-text">
        {{ details.label }}
        <AmountDisplay
          show-currency="symbol"
          fiat-currency="USD"
          :value="child.usdValue"
          :loading="child.loading"
          class="font-medium"
        />
      </div>
    </ListItem>
  </RouterLink>
</template>

<style module lang="scss">
.sub-item {
  @apply relative;
  @apply pl-16 #{!important};

  &:after {
    @apply absolute opacity-50 border-rui-text-secondary border-b border-l;
    @apply w-4 min-h-[1rem] h-[40%] top-[15%] left-10;
    content: '';
  }
}
</style>
