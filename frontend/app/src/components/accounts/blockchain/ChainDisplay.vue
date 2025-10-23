<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import ListItem from '@/components/common/ListItem.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import EvmChainIcon from '@/components/helper/display/icons/EvmChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';

const props = withDefaults(
  defineProps<{
    chain: string;
    evmChain?: boolean;
    dense?: boolean;
  }>(),
  {
    dense: false,
    evmChain: false,
  },
);

const { t } = useI18n({ useScope: 'global' });
const { chain } = toRefs(props);

const { getChainName } = useSupportedChains();
const name = computed(() => {
  const chainVal = get(chain);
  if (chainVal === 'evm')
    return t('account_form.labels.all_supported_chains');

  return get(getChainName(chain));
});

const evmChainsRepresentative = [Blockchain.ETH, Blockchain.ARBITRUM_ONE, Blockchain.BASE, Blockchain.OPTIMISM];
</script>

<template>
  <ListItem
    size="sm"
    :title="name"
    no-padding
    no-hover
    class="!py-0"
  >
    <template #avatar>
      <AdaptiveWrapper v-if="chain === 'evm'">
        <div class="grid grid-cols-2 gap-0.5">
          <ChainIcon
            v-for="item in evmChainsRepresentative"
            :key="item"
            :size="dense ? '9px' : '13px'"
            class="!p-0"
            :chain="item"
          />
        </div>
      </AdaptiveWrapper>

      <AdaptiveWrapper v-if="evmChain">
        <EvmChainIcon
          :chain="chain"
          :size="dense ? '20px' : '26px'"
        />
      </AdaptiveWrapper>

      <ChainIcon
        v-else
        :chain="chain"
        :size="dense ? '20px' : '26px'"
      />
    </template>
  </ListItem>
</template>
