<script setup lang="ts">
import Fragment from '@/components/helper/Fragment';
import { Routes } from '@/router/routes';
import {
  type BlockchainTotal,
  SupportedSubBlockchainProtocolData
} from '@/types/blockchain';
import { toSentenceCase } from '@/utils/text';
import { type ActionDataEntry } from '@/types/action';

const props = defineProps<{
  total: BlockchainTotal;
}>();

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
      class="blockchain-balance-box__item min-h-[2.25rem] group"
      :to="`${balanceBlockchainRoute}#blockchain-balances-${total.chain}`"
    >
      <VListItemAvatar tile class="grayscale group-hover:grayscale-0 m-0 mr-1">
        <ChainIcon size="26px" :chain="chain" />
      </VListItemAvatar>
      <VListItemContent>
        <div class="flex flex-wrap justify-between gap-2">
          <span>
            {{ toSentenceCase(name) }}
          </span>
          <AmountDisplay
            show-currency="symbol"
            fiat-currency="USD"
            :value="amount"
            :loading="loading"
          />
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
