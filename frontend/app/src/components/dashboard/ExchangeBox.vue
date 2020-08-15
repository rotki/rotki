<template>
  <v-list-item
    :id="`${name}_box`"
    :to="`/accounts-balances/exchange-balances/${name}`"
    :ripple="false"
    class="exchange-box__item"
  >
    <v-list-item-avatar tile class="exchange-box__icon">
      <balance-location-icon :name="name"></balance-location-icon>
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title class="d-flex justify-space-between">
        <span>
          {{ name | capitalize }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            fiat-currency="USD"
            :value="amount"
          ></amount-display>
        </span>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import BalanceLocationIcon from '@/components/dashboard/BalanceLocationIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';

@Component({
  components: { AmountDisplay, BalanceLocationIcon }
})
export default class ExchangeBox extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;
}
</script>
<style scoped lang="scss">
.exchange-box {
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
