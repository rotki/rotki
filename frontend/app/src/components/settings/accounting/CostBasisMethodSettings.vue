<script setup lang="ts">
import { useListeners } from 'vue';

const rootAttrs = useAttrs();
const rootListeners = useListeners();
const { costBasisMethodData } = useCostBasisMethod();
</script>

<template>
  <VSelect
    v-bind="rootAttrs"
    outlined
    persistent-hint
    item-value="identifier"
    item-text="identifier"
    :items="costBasisMethodData"
    v-on="rootListeners"
  >
    <template #item="{ item, attrs, on }">
      <ListItem
        no-padding
        no-hover
        v-bind="attrs"
        :subtitle="item.label"
        v-on="on"
      >
        <template #title>
          <span class="text-uppercase">{{ item.identifier }}</span>
        </template>
      </ListItem>
    </template>
    <template #selection="{ item }">
      <span class="font-medium text-uppercase">{{ item.identifier }}</span>
    </template>
  </VSelect>
</template>
