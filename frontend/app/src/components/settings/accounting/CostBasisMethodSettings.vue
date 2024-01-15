<script setup lang="ts">
const rootAttrs = useAttrs();
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
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
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
          <span class="uppercase">{{ item.identifier }}</span>
        </template>
      </ListItem>
    </template>
    <template #selection="{ item }">
      <span class="font-medium uppercase">{{ item.identifier }}</span>
    </template>
  </VSelect>
</template>
