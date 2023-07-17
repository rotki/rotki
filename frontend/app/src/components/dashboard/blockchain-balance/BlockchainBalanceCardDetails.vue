<script setup lang="ts">
import { type PropType } from 'vue';
import { type SubBlockchainTotal } from '@/types/blockchain';
import { type ActionDataEntry } from '@/types/action';

defineProps({
  child: {
    required: true,
    type: Object as PropType<SubBlockchainTotal>
  },
  details: {
    required: false,
    type: Object as PropType<ActionDataEntry | null>,
    default: null
  }
});
</script>

<template>
  <VListItem
    v-if="details"
    :id="`${child.protocol}_box`"
    :key="child.protocol"
    class="d-flex flex-row blockchain-balance-box__item sub-item"
    :to="details.detailPath"
  >
    <VListItemAvatar tile class="blockchain-balance-box__icon shrink pl-12">
      <AdaptiveWrapper class="d-flex">
        <VImg :src="details.icon" width="24px" height="24px" />
      </AdaptiveWrapper>
    </VListItemAvatar>
    <VListItemContent>
      <div class="d-flex flex-row ps-2">
        <span class="flex-grow-1 flex-shrink-1">
          {{ details.label }}
        </span>
        <span class="ml-2 text-end shrink">
          <AmountDisplay
            show-currency="symbol"
            fiat-currency="USD"
            :value="child.usdValue"
            :loading="child.loading"
          />
        </span>
      </div>
    </VListItemContent>
  </VListItem>
</template>

<style scoped lang="scss">
.blockchain-balance-box {
  &__icon {
    filter: grayscale(100%);
    margin: 0;
    margin-right: 5px !important;
    width: auto !important;
  }

  &__item:hover &__icon {
    filter: grayscale(0);
  }
}

.sub-item {
  &:after {
    opacity: 0.75 !important;
    position: absolute;
    border-bottom: 1px solid rgb(100, 100, 100);
    border-left: 1px solid rgb(100, 100, 100);
    content: '' !important;
    display: inline-block;
    left: 2.2rem;
    top: 0.7rem;
    height: 1rem;
    width: 1rem;
    min-width: 1rem;
    min-height: 1rem;
  }
}

.theme {
  &--dark {
    .sub-item {
      &:after {
        color: var(--v-dark-base);
        border-bottom: 1px solid rgb(200, 200, 200);
        border-left: 1px solid rgb(200, 200, 200);
      }
    }
  }
}
</style>
