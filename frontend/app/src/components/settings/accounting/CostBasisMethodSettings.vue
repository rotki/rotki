<script setup lang="ts">
const rootAttrs = useAttrs();
const { costBasisMethodData } = useCostBasisMethod();
</script>

<template>
  <RuiMenuSelect
    v-bind="rootAttrs"
    :options="costBasisMethodData"
    key-attr="identifier"
    variant="outlined"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #selection="{ item }">
      <span class="font-medium uppercase">{{ item.identifier }}</span>
    </template>
    <template #item="{ item }">
      <ListItem
        no-padding
        no-hover
        class="!py-0"
        :title="item.identifier.toUpperCase()"
        :subtitle="item.label"
      />
    </template>
  </RuiMenuSelect>
</template>
