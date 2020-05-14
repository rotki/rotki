<template>
  <v-list-item
    :id="`${name}_box`"
    :ripple="false"
    class="manual-balance-box__item"
    to="/blockchain-accounts"
    @click="doNothing"
  >
    <v-list-item-avatar tile class="manual-balance-box__icon">
      <v-icon>
        fa fa-{{ manualBalanceIcons[name.replace(/\s+/g, '')] }}
      </v-icon>
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title class="d-flex justify-space-between">
        <span>
          {{ name[0].toUpperCase() + name.slice(1) }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            :fiat-currency="currency.ticker_symbol"
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
import { createNamespacedHelpers } from 'vuex';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Currency } from '@/model/currency';

const { mapGetters: mapBalanceGetters } = createNamespacedHelpers('balances'); // this is only until we deprecate fiat balances
const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { AmountDisplay },
  computed: {
    ...mapGetters(['currency']),
    ...mapBalanceGetters(['fiatTotal']) // this is only until we deprecate fiat balances
  }
})
export default class ManualBalanceCardList extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;

  currency!: Currency;
  fiatTotal!: BigNumber; // this is only until we deprecate fiat balances
  manualBalanceIcons = {
    external: 'book',
    banks: 'bank',
    equities: 'suitcase',
    realestate: 'home',
    commodities: 'shopping-basket',
    fiat: 'money',
    blockchain: 'link'
  };

  doNothing() {}
}
</script>
<style scoped lang="scss">
.manual-balance-box__currency__symbol {
  font-size: 2em;
}

.manual-balance-box__icon {
  filter: grayscale(100%);
}

.manual-balance-box__item:hover .manual-balance-box__icon {
  filter: grayscale(0);
}

.manual-balance-box__icon--inverted {
  margin-left: 8px;
  width: 45px;
  filter: grayscale(100%) invert(100%);
}
</style>
