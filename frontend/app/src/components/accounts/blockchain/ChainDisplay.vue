<script setup lang="ts">
import { useSupportedChains } from '@/composables/info/chains';
import ChainIcon from '@/components/helper/display/icons/ChainIcon.vue';
import ListItem from '@/components/common/ListItem.vue';

const props = withDefaults(
  defineProps<{
    chain: string;
    dense?: boolean;
  }>(),
  {
    dense: false,
  },
);

const { chain } = toRefs(props);

const { getChainName } = useSupportedChains();
const name = getChainName(chain);
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
      <ChainIcon
        :chain="chain"
        :size="dense ? '20px' : '26px'"
      />
    </template>
  </ListItem>
</template>
