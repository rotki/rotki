<script setup lang="ts">
import ListItem from '@/components/common/ListItem.vue';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import { useSupportedChains } from '@/composables/info/chains';
import { Blockchain } from '@rotki/common';

const props = withDefaults(
  defineProps<{
    chain: string;
    dense?: boolean;
  }>(),
  {
    dense: false,
  },
);

const { t } = useI18n();
const { chain } = toRefs(props);

const { getChainName } = useSupportedChains();
const name = computed(() => {
  const chainVal = get(chain);
  if (chainVal === 'evm')
    return t('account_form.labels.all_supported_chains');

  return get(getChainName(chain));
});
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
            v-for="item in [Blockchain.ETH, Blockchain.ARBITRUM_ONE, Blockchain.BASE, Blockchain.OPTIMISM]"
            :key="item"
            :size="dense ? '10px' : '13px'"
            class="!p-0"
            :chain="item"
          />
        </div>
      </AdaptiveWrapper>

      <ChainIcon
        v-else
        :chain="chain"
        :size="dense ? '20px' : '26px'"
      />
    </template>
  </ListItem>
</template>
