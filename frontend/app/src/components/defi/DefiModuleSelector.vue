<script setup lang="ts">
import { useListeners } from 'vue';
import {
  type Module,
  SUPPORTED_MODULES,
  type SupportedModule
} from '@/types/modules';

defineOptions({
  inheritAttrs: false
});

const props = withDefaults(
  defineProps<{
    value?: string;
    items?: Module[];
    attach?: string;
  }>(),
  {
    value: '',
    items: () => [],
    attach: undefined
  }
);

const emit = defineEmits<{
  (e: 'change', value: string): void;
}>();

const rootAttrs = useAttrs();
const listeners = useListeners();

const { items } = toRefs(props);

const change = (_value: string) => emit('change', _value);

const modules = computed<SupportedModule[]>(() => {
  const itemsVal = get(items);

  return SUPPORTED_MODULES.filter(item =>
    itemsVal && itemsVal.length > 0 ? itemsVal.includes(item.identifier) : true
  );
});
</script>

<template>
  <VAutocomplete
    v-bind="rootAttrs"
    data-cy="defi-input"
    :value="value"
    :items="modules"
    :attach="attach"
    item-value="identifier"
    item-text="name"
    auto-select-first
    @input="change($event)"
    v-on="listeners"
  >
    <template #selection="{ attrs, item }">
      <DefiIcon v-bind="attrs" :item="item" />
    </template>
    <template #item="{ attrs, item }">
      <DefiIcon v-bind="attrs" :item="item" />
    </template>
  </VAutocomplete>
</template>
