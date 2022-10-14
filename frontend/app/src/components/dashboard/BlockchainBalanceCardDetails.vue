<template>
  <v-list-item
    v-if="details"
    :id="`${child.protocol}_box`"
    :key="child.protocol"
    class="d-flex flex-row blockchain-balance-box__item sub-item"
    :to="details.detailPath"
  >
    <v-list-item-avatar tile class="blockchain-balance-box__icon shrink pl-12">
      <adaptive-wrapper class="d-flex">
        <v-img :src="details.icon" width="24px" height="24px" />
      </adaptive-wrapper>
    </v-list-item-avatar>
    <v-list-item-content>
      <div class="d-flex flex-row ps-2">
        <span class="flex-grow-1 flex-shrink-1">
          {{ details.label }}
        </span>
        <span class="ml-2 text-end shrink">
          <amount-display
            show-currency="symbol"
            fiat-currency="USD"
            :value="child.usdValue"
            :loading="child.loading"
          />
        </span>
      </div>
    </v-list-item-content>
  </v-list-item>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import { ActionDataEntry } from '@/store/types';
import { SubBlockchainTotal } from '@/types/blockchain';

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
