<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const { costBasisMethodData } = useCostBasisMethod();
</script>

<template>
  <VSelect
    v-bind="$attrs"
    variant="outlined"
    persistent-hint
    item-value="identifier"
    item-title="identifier"
    :items="costBasisMethodData"
  >
    <template #item="{ item, props }">
      <ListItem
        no-padding
        no-hover
        v-bind="props"
        :subtitle="item.raw.label"
      >
        <template #title>
          <span class="uppercase">{{ item.raw.identifier }}</span>
        </template>
      </ListItem>
    </template>
    <template #selection="{ item }">
      <span class="font-medium uppercase">{{ item.raw.identifier }}</span>
    </template>
  </VSelect>
</template>
