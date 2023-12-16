<script lang="ts" setup>
defineOptions({
  inheritAttrs: false,
});

const modelValue = defineModel<string | undefined>({ required: true });

const { counterparties } = useHistoryEventCounterpartyMappings();
</script>

<template>
  <RuiAutoComplete
    v-model="modelValue"
    variant="outlined"
    clearable
    v-bind="$attrs"
    auto-select-first
    :options="counterparties"
  >
    <template #item="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
    <template #selection="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
  </RuiAutoComplete>
</template>
