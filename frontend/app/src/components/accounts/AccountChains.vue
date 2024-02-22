<script lang="ts" setup>
type Row = { chain: string } | { chains: string[] };

const props = defineProps<{ row: Row }>();

const chains = computed<string[]>(() => {
  const row = props.row;
  return 'chains' in row ? row.chains : [row.chain];
});
</script>

<template>
  <div class="flex">
    <template
      v-for="chain in chains"
      :key="chain"
    >
      <ChainIcon :chain="chain" />
    </template>
  </div>
</template>
