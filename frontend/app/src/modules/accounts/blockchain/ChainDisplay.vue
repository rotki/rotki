<script setup lang="ts">
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSetting } from '@/modules/settings/use-setting';
import ChainIcon from '@/modules/shell/components/ChainIcon.vue';
import EvmChainIcon from '@/modules/shell/components/EvmChainIcon.vue';
import ListItem from '@/modules/shell/components/ListItem.vue';

const { chain, dense = false, evmChain = false } = defineProps<{
  chain: string;
  evmChain?: boolean;
  dense?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { getChainName } = useSupportedChains();
const shouldShowAmount = useSetting('shouldShowAmount');
const name = computed(() => {
  if (chain === 'all')
    return t('account_form.labels.all_supported_chains');

  return getChainName(chain);
});
</script>

<template>
  <!-- `inline` keeps the avatar box at the icon's 24px, so an option is as tall as ChainSelect's item-height says -->
  <ListItem
    size="sm"
    inline
    :title="name"
    no-padding
    no-hover
    class="py-0!"
    :blur-content="!shouldShowAmount"
  >
    <template #avatar>
      <!-- one mark for "every chain", not four logos too small to read -->
      <div
        v-if="chain === 'all'"
        class="rounded-full bg-rui-primary/10 text-rui-primary flex items-center justify-center"
        :class="dense ? 'size-5' : 'size-6'"
      >
        <RuiIcon
          name="lu-layers"
          :size="dense ? 12 : 14"
        />
      </div>

      <EvmChainIcon
        v-else-if="evmChain"
        class="icon-bg"
        :chain="chain"
        :size="dense ? '20px' : '24px'"
      />

      <ChainIcon
        v-else
        :chain="chain"
        :size="dense ? '20px' : '24px'"
      />
    </template>
  </ListItem>
</template>
