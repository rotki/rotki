<template>
  <v-list-item
    :id="`${name}_box`"
    :ripple="false"
    class="manual-balance-box__item"
    to="/accounts-balances/manual-balances"
  >
    <v-list-item-avatar tile class="manual-balance-box__icon">
      <location-display :identifier="name" icon />
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title class="d-flex justify-space-between">
        <span>
          {{ name | capitalize }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            :fiat-currency="currency.ticker_symbol"
            :value="amount"
          />
        </span>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Currency } from '@/model/currency';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { AmountDisplay },
  computed: {
    ...mapGetters(['currency'])
  }
})
export default class ManualBalanceCardList extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;

  currency!: Currency;
}
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
