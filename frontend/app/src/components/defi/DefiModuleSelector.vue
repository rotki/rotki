<script setup lang="ts">
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
  (e: 'input', value: string): void;
}>();

const model = useSimpleVModel(props, emit);

const modules = computed<SupportedModule[]>(() => {
  const items = props.items;

  return SUPPORTED_MODULES.filter(item =>
    items && items.length > 0 ? items.includes(item.identifier) : true
  );
});
</script>

<template>
  <VAutocomplete
    v-bind="$attrs"
    v-model="model"
    data-cy="defi-input"
    :items="modules"
    :attach="attach"
    item-value="identifier"
    item-text="name"
    auto-select-first
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #selection="{ attrs, item }">
      <DefiIcon v-bind="attrs" :item="item" />
    </template>
    <template #item="{ attrs, item }">
      <DefiIcon v-bind="attrs" :item="item" />
    </template>
  </VAutocomplete>
</template>
