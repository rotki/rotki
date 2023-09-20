<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { toSentenceCase } from '@/utils/text';

defineProps({
  name: {
    required: true,
    type: String
  },
  amount: {
    required: true,
    type: BigNumber
  }
});

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
</script>

<template>
  <VListItem
    :id="`${name}_box`"
    :ripple="false"
    :data-cy="`manual-balance-box__item__${name}`"
    class="manual-balance-box__item"
    to="/accounts-balances/manual-balances"
  >
    <VListItemAvatar tile class="manual-balance-box__icon">
      <LocationDisplay :identifier="name" icon />
    </VListItemAvatar>
    <VListItemContent>
      <VListItemTitle class="flex justify-between">
        <span>
          {{ toSentenceCase(name) }}
        </span>
        <span class="text-end">
          <AmountDisplay
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :value="amount"
          />
        </span>
      </VListItemTitle>
    </VListItemContent>
  </VListItem>
</template>

<style scoped lang="scss">
.manual-balance-box {
  &__icon {
    filter: grayscale(100%);
    margin: 0;
    margin-right: 5px !important;
  }

  &__item:hover &__icon {
    filter: grayscale(0);
  }
}
</style>
