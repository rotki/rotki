<script setup lang="ts">
import { type PropType } from 'vue';
import Fragment from '@/components/helper/Fragment';
import { Routes } from '@/router/routes';
import {
  type BlockchainTotal,
  SupportedSubBlockchainProtocolData
} from '@/types/blockchain';
import { toSentenceCase } from '@/utils/text';
import { type ActionDataEntry } from '@/types/action';

const props = defineProps({
  total: { required: true, type: Object as PropType<BlockchainTotal> }
});

const { total } = toRefs(props);

const { getChainName } = useSupportedChains();

const chain = useRefMap(total, ({ chain }) => chain);
const name = getChainName(chain);

const childData = (identifier: string): ActionDataEntry | null =>
  SupportedSubBlockchainProtocolData.find(
    item => item.identifier === identifier
  ) || null;

const amount = useRefMap(total, ({ usdValue }) => usdValue);
const loading = useRefMap(total, ({ loading }) => loading);

const balanceBlockchainRoute = Routes.ACCOUNTS_BALANCES_BLOCKCHAIN;
</script>

<template>
  <Fragment>
    <VListItem
      :id="`${name}_box`"
      :data-cy="`blockchain-balance-box__item__${name}`"
      class="blockchain-balance-box__item"
      :to="`${balanceBlockchainRoute}#blockchain-balances-${total.chain}`"
    >
      <VListItemAvatar tile class="blockchain-balance-box__icon">
        <AssetIcon size="24px" :identifier="chain" :show-chain="false" />
      </VListItemAvatar>
      <VListItemContent>
        <div class="flex flex-row">
          <span class="grow shrink">
            {{ toSentenceCase(name) }}
          </span>
          <span class="ml-2 text-end shrink">
            <AmountDisplay
              show-currency="symbol"
              fiat-currency="USD"
              :value="amount"
              :loading="loading"
            />
          </span>
        </div>
      </VListItemContent>
    </VListItem>
    <VList v-if="total.children.length > 0" class="pa-0">
      <template v-for="child in total.children">
        <BlockchainBalanceCardDetails
          :key="child.protocol"
          :child="child"
          :details="childData(child.protocol)"
        />
      </template>
    </VList>
  </Fragment>
</template>

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
</style>
