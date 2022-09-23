<template>
  <v-list-item
    :id="`${name}_box`"
    :ripple="false"
    :data-cy="`manual-balance-box__item__${name}`"
    class="manual-balance-box__item"
    to="/accounts-balances/manual-balances"
  >
    <v-list-item-avatar tile class="manual-balance-box__icon">
      <location-display :identifier="name" icon />
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title class="d-flex justify-space-between">
        <span>
          {{ toSentenceCase(name) }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            :fiat-currency="currencySymbol"
            :value="amount"
          />
        </span>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { useGeneralSettingsStore } from '@/store/settings/general';
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
