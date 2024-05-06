<script setup lang="ts">
const rootAttrs = useAttrs();
const { costBasisMethodData } = useCostBasisMethod();
</script>

<template>
  <RuiMenuSelect
    v-bind="rootAttrs"
    :options="costBasisMethodData"
    key-attr="identifier"
    text-attr="label"
    full-width
    show-details
    variant="outlined"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #activator.text="{ value }">
      <span class="font-medium uppercase">{{ value.identifier }}</span>
    </template>
    <template #item.text="{ option }">
      <ListItem
        no-padding
        no-hover
        class="!py-0"
        :title="option.identifier.toUpperCase()"
        :subtitle="option.label"
      />
    </template>
  </RuiMenuSelect>
</template>
