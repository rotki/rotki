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

const { counterparties } = useHistoryEventMappings();
</script>

<template>
  <ComboboxWithCustomInput
    v-model="vModel"
    outlined
    required
    clearable
    v-bind="rootAttrs"
    auto-select-first
    :items="counterparties"
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  />
</template>
