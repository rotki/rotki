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
  <RouterLink v-if="details" :to="details.detailPath || ''">
    <ListItem
      :id="`${child.protocol}_box`"
      :key="child.protocol"
      class="blockchain-balance-box__item group py-1"
      :class="css['sub-item']"
    >
      <template #avatar>
        <div class="grayscale group-hover:grayscale-0">
          <AdaptiveWrapper>
            <AppImage :src="details.icon" width="24px" height="24px" />
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
  @apply pl-14 #{!important};

  &:after {
    @apply absolute opacity-50 border-rui-text-secondary border-b border-l;
    @apply w-4 min-h-[1rem] h-[40%] top-[15%] left-8;
    content: '';
  }
}
</style>
