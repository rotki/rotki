<template>
  <v-list-item
    v-if="amount !== zero"
    :id="`${name}_box`"
    :ripple="false"
    class="blockchain-balance-box__item"
    @click="doNothing"
  >
    <v-list-item-avatar
      tile
      class="blockchain-balance-box__icon blockchain-box__icon"
    >
      <crypto-icon
        width="24px"
        :symbol="blockchainBalanceIcons[name]"
      ></crypto-icon>
    </v-list-item-avatar>
    <v-list-item-content>
      <v-list-item-title
        style="display: flex; justify-content: space-between;"
        class="font-weight-light"
      >
        <span>
          {{ name[0].toUpperCase() + name.slice(1) }}
        </span>
        <span class="text-end">
          <amount-display
            show-currency="symbol"
            fiat
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
import CryptoIcon from '@/components/CryptoIcon.vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: { AmountDisplay, CryptoIcon }
})
export default class BlockchainBalanceCardList extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: BigNumber;

  zero = Zero;

  blockchainBalanceIcons = {
    bitcoin: 'BTC',
    ethereum: 'ETC'
  };

  doNothing() {}
}
</script>
<style scoped lang="scss">
.blockchain-balance-box__currency__symbol {
  font-size: 2em;
}

.blockchain-balance-box__icon {
  filter: grayscale(100%);
}

.blockchain-balance-box__item:hover .blockchain-balance-box__icon {
  filter: grayscale(0);
}

.blockchain-balance-box__icon--inverted {
  margin-left: 8px;
  width: 45px;
  filter: grayscale(100%) invert(100%);
}
</style>
