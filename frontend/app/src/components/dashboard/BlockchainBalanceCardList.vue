<template>
  <fragment>
    <v-list-item
      :id="`${name}_box`"
      class="blockchain-balance-box__item"
      to="/accounts-balances/blockchain-balances"
    >
      <v-list-item-avatar tile class="blockchain-balance-box__icon">
        <crypto-icon size="24px" :symbol="chain" />
      </v-list-item-avatar>
      <v-list-item-content>
        <div class="d-flex flex-row">
          <span class="grow">
            {{ name | capitalize }}
          </span>
          <span class="text-end shrink">
            <amount-display
              show-currency="symbol"
              fiat-currency="USD"
              :value="amount"
              :loading="loading"
            />
          </span>
        </div>
      </v-list-item-content>
    </v-list-item>
    <v-list v-if="total.l2.length > 0" class="pa-0">
      <v-list-item
        v-for="l2 in total.l2"
        :id="`${l2.protocol}_box`"
        :key="l2.protocol"
        class="d-flex flex-row blockchain-balance-box__item"
        to="/accounts-balances/blockchain-balances"
      >
        <v-list-item-avatar
          tile
          class="blockchain-balance-box__icon shrink ps-14"
        >
          <crypto-icon size="24px" :symbol="l2.protocol" />
        </v-list-item-avatar>
        <v-list-item-content>
          <div class="d-flex flex-row ps-2">
            <span class="grow">
              {{ l2Name(l2.protocol) }}
            </span>
            <span class="text-end shrink">
              <amount-display
                show-currency="symbol"
                fiat-currency="USD"
                :value="l2.usdValue"
                :loading="l2.loading"
              />
            </span>
          </div>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </fragment>
</template>

<script lang="ts">
import { default as BigNumber } from 'bignumber.js';
import { Component, Prop, Vue } from 'vue-property-decorator';
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import Fragment from '@/components/helper/Fragment';
import { BlockchainTotal } from '@/store/balances/types';
import {
  Blockchain,
  BTC,
  ETH,
  KSM,
  L2_LOOPRING,
  SupportedL2Protocol
} from '@/typing/types';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: { Fragment, AmountDisplay, CryptoIcon }
})
export default class BlockchainBalanceCardList extends Vue {
  @Prop({ required: true, type: Object })
  total!: BlockchainTotal;

  get name(): string {
    const chain = this.total.chain;
    if (chain === ETH) {
      return this.$t('blockchains.eth').toString();
    } else if (chain === BTC) {
      return this.$t('blockchains.btc').toString();
    } else if (chain === KSM) {
      return this.$t('blockchains.ksm').toString();
    }
    return '';
  }

  l2Name(protocol: SupportedL2Protocol) {
    if (protocol === L2_LOOPRING) {
      return this.$t('l2.loopring').toString();
    }
    return '';
  }

  get amount(): BigNumber {
    return this.total.usdValue;
  }

  get chain(): Blockchain {
    return this.total.chain;
  }

  get loading(): boolean {
    return this.total.loading;
  }

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
