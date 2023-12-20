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
    <RouterLink
      :to="`${balanceBlockchainRoute}#blockchain-balances-${total.chain}`"
    >
      <ListItem
        data-cy="blockchain-balance__summary"
        :data-location="total.chain"
        class="group py-1"
      >
        <template #avatar>
          <div class="grayscale group-hover:grayscale-0">
            <ChainIcon size="24px" :chain="chain" />
          </div>
        </template>
        <div class="flex flex-wrap justify-between gap-1 text-rui-text">
          {{ toSentenceCase(name) }}
          <AmountDisplay
            show-currency="symbol"
            fiat-currency="USD"
            :value="amount"
            :loading="loading"
            class="font-medium"
          />
        </div>
      </ListItem>
    </RouterLink>
    <div v-if="total.children.length > 0">
      <template v-for="child in total.children">
        <BlockchainBalanceCardDetails
          :key="child.protocol"
          :child="child"
          :details="childData(child.protocol)"
        />
      </template>
    </div>
  </Fragment>
</template>
