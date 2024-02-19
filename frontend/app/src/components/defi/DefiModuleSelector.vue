<script setup lang="ts">
import {
  type Module,
  SUPPORTED_MODULES,
  type SupportedModule,
} from '@/types/modules';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    modelValue?: string;
    items?: Module[];
    attach?: string;
  }>(),
  {
    modelValue: '',
    items: () => [],
    attach: undefined,
  },
);

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
}>();

const model = useSimpleVModel(props, emit);

const modules = computed<SupportedModule[]>(() => {
  const items = props.items;

  return SUPPORTED_MODULES.filter(item =>
    items && items.length > 0 ? items.includes(item.identifier) : true,
  );
});
</script>

<template>
  <VAutocomplete
    v-bind="$attrs"
    v-model="model"
    data-cy="defi-input"
    :items="modules"
    item-value="identifier"
    item-title="name"
    auto-select-first
  >
    <template #selection="{ item }">
      <DefiIcon
        :item="item.raw"
      />
    </template>
    <template #item="{ item }">
      <DefiIcon
        :item="item.raw"
      />
    </template>
  </VAutocomplete>
</template>
