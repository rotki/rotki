<template>
  <v-list-item
    :id="`${name}_box`"
    :ripple="false"
    to="/accounts-balances/blockchain-balances"
    class="blockchain-balance-box__item"
  >
    <v-list-item-avatar tile class="blockchain-balance-box__icon">
      <crypto-icon size="24px" :symbol="chain" />
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
            :loading="loading"
          />
        </span>
      </v-list-item-title>
    </v-list-item-content>
  </v-list-item>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Blockchain } from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: { AmountDisplay, CryptoIcon }
})
export default class BlockchainBalanceCardList extends Vue {
  @Prop({ required: true, type: String })
  name!: string;
  @Prop({ required: true, type: Object })
  amount!: BigNumber;
  @Prop({ required: true, type: String })
  chain!: Blockchain;
  @Prop({ required: true, type: Boolean })
  loading!: boolean;

  zero = Zero;
}
</script>
<style scoped lang="scss">
.blockchain-balance-box {
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
