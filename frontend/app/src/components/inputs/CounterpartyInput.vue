<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    value?: string | null;
  }>(),
  {
    value: null,
  },
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
}>();

const vModel = useSimpleVModel(props, emit);

const rootAttrs = useAttrs();

const { counterparties } = useHistoryEventCounterpartyMappings();
</script>

<template>
  <RuiAutoComplete
    v-model="vModel"
    variant="outlined"
    clearable
    v-bind="rootAttrs"
    auto-select-first
    :options="counterparties"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #item="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
    <template #selection="{ item }">
      <CounterpartyDisplay :counterparty="item" />
    </template>
  </RuiAutoComplete>
</template>
