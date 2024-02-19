<script setup lang="ts">
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
    :size="dense ? 'sm' : 'md'"
    :title="name"
    no-padding
    no-hover
  >
    <template #avatar>
      <ChainIcon :chain="chain" />
    </template>
  </ListItem>
</template>
