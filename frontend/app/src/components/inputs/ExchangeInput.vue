<script lang="ts" setup>
const props = withDefaults(
  defineProps<{
    modelValue?: string | null;
    dense?: boolean;
    showWithKeyOnly?: boolean;
  }>(),
  {
    modelValue: null,
    showWithKeyOnly: false,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
}>();

const vModel = useSimpleVModel(props, emit);

const { allExchanges, exchangesWithKey } = storeToRefs(useLocationStore());
</script>

<template>
  <RuiAutoComplete
    v-model="vModel"
    variant="outlined"
    v-bind="$attrs"
    :options="showWithKeyOnly ? exchangesWithKey : allExchanges"
    :dense="dense"
    :item-height="52"
    auto-select-first
  >
    <template #selection="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="`exchange__${item}`"
      />
    </template>
    <template #item="{ item }">
      <ExchangeDisplay
        :exchange="item"
        :class="[`exchange__${item}`, dense && 'py-2']"
      />
    </template>
  </RuiAutoComplete>
</template>
