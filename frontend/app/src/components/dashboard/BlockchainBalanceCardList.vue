<template>
  <fragment>
    <v-list-item
      :id="`${name}_box`"
      :data-cy="`blockchain-balance-box__item__${name}`"
      class="blockchain-balance-box__item"
      :to="`/accounts-balances/blockchain-balances#blockchain-balances-${total.chain}`"
    >
      <v-list-item-avatar tile class="blockchain-balance-box__icon">
        <asset-icon size="24px" :identifier="chain" />
      </v-list-item-avatar>
      <v-list-item-content>
        <div class="d-flex flex-row">
          <span class="grow">
            {{ capitalize(name) }}
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
        class="d-flex flex-row blockchain-balance-box__item sub-item"
        :to="`/accounts-balances/blockchain-balances#blockchain-balances-${l2.protocol}`"
      >
        <v-list-item-avatar
          tile
          class="blockchain-balance-box__icon shrink ps-14"
        >
          <asset-icon
            size="24px"
            :identifier="getIdentifierForSymbol(l2.protocol)"
          />
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
import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { Component, Mixins, Prop } from 'vue-property-decorator';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import Fragment from '@/components/helper/Fragment';
import { capitalize } from '@/filters';
import AssetMixin from '@/mixins/asset-mixin';
import { BlockchainTotal } from '@/store/balances/types';
import { L2_LOOPRING, SupportedL2Protocol } from '@/types/protocols';
import { Zero } from '@/utils/bignumbers';

@Component({
  components: { Fragment, AmountDisplay, AssetIcon }
})
export default class BlockchainBalanceCardList extends Mixins(AssetMixin) {
  @Prop({ required: true, type: Object })
  total!: BlockchainTotal;

  readonly capitalize = capitalize;

  get name(): string {
    const chain = this.total.chain;
    if (chain === Blockchain.ETH) {
      return this.$t('blockchains.eth').toString();
    } else if (chain === Blockchain.BTC) {
      return this.$t('blockchains.btc').toString();
    } else if (chain === Blockchain.KSM) {
      return this.$t('blockchains.ksm').toString();
    } else if (chain === Blockchain.DOT) {
      return this.$t('blockchains.dot').toString();
    } else if (chain === Blockchain.AVAX) {
      return this.$t('blockchains.avax').toString();
    } else if (chain === Blockchain.ETH2) {
      return this.$t('blockchains.eth2').toString();
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

.sub-item {
  &:before {
    opacity: 0.75 !important;
    position: relative;
    top: -0.3em;
    height: 1em;
    width: 1em;
    color: white;
    border-bottom: 1px solid rgb(100, 100, 100);
    content: '' !important;
    display: inline-block;
    left: 20px;
  }

  &:last-child {
    border-left: none;

    &:before {
      border-left: 1px solid rgb(100, 100, 100);
    }
  }
}

.theme {
  &--dark {
    .sub-item {
      &:before {
        color: var(--v-dark-base);
        border-bottom: 1px solid rgb(200, 200, 200);
      }

      &:last-child {
        &:before {
          border-left: 1px solid rgb(200, 200, 200);
        }
      }
    }
  }
}
</style>
