<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import type { BlockchainTotal } from '@/types/blockchain';
import { Blockchain, toSentenceCase } from '@rotki/common';
import Eth2ValidatorLimitTooltip from '@/components/accounts/blockchain/eth2/Eth2ValidatorLimitTooltip.vue';
import ListItem from '@/components/common/ListItem.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { useRefMap } from '@/composables/utils/useRefMap';

interface BlockChainBalanceCardListProps {
  total: BlockchainTotal;
}

const props = defineProps<BlockChainBalanceCardListProps>();

const { total } = toRefs(props);

const { getBlockchainRedirectLink, getChainName } = useSupportedChains();

const chain = useRefMap(total, ({ chain }) => chain);
const name = getChainName(chain);

const navTarget = computed<RouteLocationRaw>(() => ({
  path: getBlockchainRedirectLink(props.total.chain),
}));
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
              force-currency
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
