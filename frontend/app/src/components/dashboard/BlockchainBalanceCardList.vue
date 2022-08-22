<template>
  <fragment>
    <v-list-item
      :id="`${name}_box`"
      :data-cy="`blockchain-balance-box__item__${name}`"
      class="blockchain-balance-box__item"
      :to="`${balanceBlockchainRoute}#blockchain-balances-${total.chain}`"
    >
      <v-list-item-avatar tile class="blockchain-balance-box__icon">
        <asset-icon size="24px" :identifier="chain" />
      </v-list-item-avatar>
      <v-list-item-content>
        <div class="d-flex flex-row">
          <span class="flex-grow-1 flex-shrink-1">
            {{ toSentenceCase(name) }}
          </span>
          <span class="ml-2 text-end shrink">
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
    <v-list v-if="total.children.length > 0" class="pa-0">
      <template v-for="child in total.children">
        <v-list-item
          v-if="childData(child.protocol)"
          :id="`${child.protocol}_box`"
          :key="child.protocol"
          class="d-flex flex-row blockchain-balance-box__item sub-item"
          :to="childData(child.protocol).detailPath"
        >
          <v-list-item-avatar
            tile
            class="blockchain-balance-box__icon shrink ps-7"
          >
            <adaptive-wrapper>
              <v-img
                :src="childData(child.protocol).icon"
                width="24px"
                height="24px"
              />
            </adaptive-wrapper>
          </v-list-item-avatar>
          <v-list-item-content>
            <div class="d-flex flex-row ps-2">
              <span class="flex-grow-1 flex-shrink-1">
                {{ childData(child.protocol).label }}
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
    </v-list>
  </fragment>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { get } from '@vueuse/core';
import { computed, defineComponent, PropType, toRefs } from 'vue';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import Fragment from '@/components/helper/Fragment';
import i18n from '@/i18n';
import { Routes } from '@/router/routes';
import { useAssetInfoRetrieval } from '@/store/assets';
import { SupportedSubBlockchainProtocolData } from '@/store/balances/const';
import { BlockchainTotal } from '@/store/balances/types';
import { ActionDataEntry } from '@/store/types';
import { toSentenceCase } from '@/utils/text';

export default defineComponent({
  name: 'BlockchainBalanceCardList',
  components: { Fragment, AmountDisplay, AssetIcon },
  props: {
    total: { required: true, type: Object as PropType<BlockchainTotal> }
  },
  setup(props) {
    const { total } = toRefs(props);

    const { getAssetIdentifierForSymbol } = useAssetInfoRetrieval();

    const name = computed<string>(() => {
      const chain = get(total).chain;

      return (
        {
          [Blockchain.ETH]: i18n.t('blockchains.eth').toString(),
          [Blockchain.ETH2]: i18n.t('blockchains.eth2').toString(),
          [Blockchain.BTC]: i18n.t('blockchains.btc').toString(),
          [Blockchain.BCH]: i18n.t('blockchains.bch').toString(),
          [Blockchain.KSM]: i18n.t('blockchains.ksm').toString(),
          [Blockchain.DOT]: i18n.t('blockchains.dot').toString(),
          [Blockchain.AVAX]: i18n.t('blockchains.avax').toString()
        }[chain] ?? ''
      );
    });

    const childData = (identifier: string): ActionDataEntry | null => {
      return (
        SupportedSubBlockchainProtocolData.find(
          item => item.identifier === identifier
        ) || null
      );
    };

    const amount = computed<BigNumber>(() => {
      return get(total).usdValue;
    });

    const chain = computed<Blockchain>(() => {
      return get(total).chain;
    });

    const loading = computed<boolean>(() => {
      return get(total).loading;
    });

    return {
      balanceBlockchainRoute: Routes.ACCOUNTS_BALANCES_BLOCKCHAIN.route,
      amount,
      chain,
      loading,
      childData,
      name,
      getAssetIdentifierForSymbol,
      toSentenceCase
    };
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
