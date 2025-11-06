<script setup lang="ts">
import { Blockchain } from '@rotki/common';
import ListItem from '@/components/common/ListItem.vue';
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
  if (chainVal === 'all')
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
      <div
        v-if="chain === 'all'"
        class="grid grid-cols-2 gap-0.5 icon-bg"
      >
        <ChainIcon
          v-for="item in evmChainsRepresentative"
          :key="item"
          :size="dense ? '9px' : '13px'"
          class="!p-0"
          :chain="item"
        />
      </div>

      <EvmChainIcon
        v-else-if="evmChain"
        class="icon-bg"
        :chain="chain"
        :size="dense ? '20px' : '26px'"
      />

      <ChainIcon
        v-else
        :chain="chain"
        :size="dense ? '20px' : '26px'"
      />
    </template>
  </ListItem>
</template>
