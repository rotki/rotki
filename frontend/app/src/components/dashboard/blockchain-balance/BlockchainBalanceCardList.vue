<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import { Routes } from '@/router/routes';
import { type BlockchainTotal, SupportedSubBlockchainProtocolData } from '@/types/blockchain';
import type { RouteLocationRaw } from 'vue-router';
import type { ActionDataEntry } from '@/types/action';

const props = defineProps<{
  total: BlockchainTotal;
}>();

const { total } = toRefs(props);

const { getChainName, getChainAccountType } = useSupportedChains();

const amount = useRefMap(total, ({ usdValue }) => usdValue);
const loading = useRefMap(total, ({ loading }) => loading);
const chain = useRefMap(total, ({ chain }) => chain);
const name = getChainName(chain);

const { unifyAccountsTable } = storeToRefs(useFrontendSettingsStore());

const navTarget = computed<RouteLocationRaw>(() => {
  let target: string;
  const balanceChain = get(chain);
  if (balanceChain === Blockchain.ETH2) {
    target = 'validators';
  }
  else {
    if (get(unifyAccountsTable))
      target = 'all';
    else
      target = getChainAccountType(balanceChain) ?? 'evm';
  }

  return {
    path: `${Routes.ACCOUNTS_BALANCES_BLOCKCHAIN}/${target}`,
    hash: '#accounts-section',
  };
});

function childData(identifier: string): ActionDataEntry | null {
  return SupportedSubBlockchainProtocolData.find(item => item.identifier === identifier) || null;
}
</script>

<template>
  <div>
    <RouterLink :to="navTarget">
      <ListItem
        data-cy="blockchain-balance__summary"
        :data-location="total.chain"
        class="group py-1 px-6"
      >
        <template #avatar>
          <div class="grayscale group-hover:grayscale-0">
            <ChainIcon
              size="24px"
              :chain="chain"
            />
          </div>
        </template>
        <div class="flex flex-wrap justify-between gap-1 text-rui-text">
          {{ toSentenceCase(name) }}

          <div class="flex gap-2 items-center">
            <Eth2ValidatorLimitTooltip v-if="chain === Blockchain.ETH2" />

            <AmountDisplay
              show-currency="symbol"
              fiat-currency="USD"
              :value="amount"
              :loading="loading"
              class="font-medium"
            />
          </div>
        </div>
      </ListItem>
    </RouterLink>
    <div v-if="total.children.length > 0">
      <template
        v-for="child in total.children"
        :key="child.protocol"
      >
        <BlockchainBalanceCardDetails
          :child="child"
          :details="childData(child.protocol)"
        />
      </template>
    </div>
  </div>
</template>
