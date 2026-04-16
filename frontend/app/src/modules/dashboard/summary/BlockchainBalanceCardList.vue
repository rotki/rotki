<script setup lang="ts">
import type { BlockchainTotal } from '@/modules/balances/blockchain-types';
import { Blockchain, toSentenceCase } from '@rotki/common';
import Eth2ValidatorLimitTooltip from '@/modules/accounts/blockchain/eth2/Eth2ValidatorLimitTooltip.vue';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';

interface BlockChainBalanceCardListProps {
  total: BlockchainTotal;
}

const { total } = defineProps<BlockChainBalanceCardListProps>();

const { useBlockchainRedirectLink, useChainName } = useSupportedChains();

const name = useChainName(() => total.chain);
const navTarget = useBlockchainRedirectLink(() => total.chain);
</script>

<template>
  <div>
    <RouterLink :to="navTarget">
      <ListItem
        data-cy="blockchain-balance__summary"
        :data-location="total.chain"
        class="group !py-1 px-6"
      >
        <template #avatar>
          <div class="grayscale group-hover:grayscale-0">
            <ChainIcon
              size="24px"
              :chain="total.chain"
            />
          </div>
        </template>
        <div class="flex flex-wrap justify-between gap-1 text-rui-text">
          {{ toSentenceCase(name) }}

          <div class="flex gap-2 items-center">
            <Eth2ValidatorLimitTooltip v-if="total.chain === Blockchain.ETH2" />

            <FiatDisplay
              :value="total.value"
              :loading="total.loading"
              class="font-medium"
            />
          </div>
        </div>
      </ListItem>
    </RouterLink>
  </div>
</template>
