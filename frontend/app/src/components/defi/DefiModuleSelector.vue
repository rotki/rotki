<script setup lang="ts">
import { type Module, SUPPORTED_MODULES, type SupportedModule } from '@/types/modules';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    items?: Module[];
  }>(),
  {
    items: () => [],
  },
);

const model = defineModel<string>({ required: true });

const modules = computed<SupportedModule[]>(() => {
  const items = props.items;

  return SUPPORTED_MODULES.filter(item => (items && items.length > 0 ? items.includes(item.identifier) : true));
});
</script>

<template>
  <RuiAutoComplete
    v-bind="$attrs"
    v-model="model"
    data-cy="defi-input"
    :options="modules"
    key-attr="identifier"
    text-attr="name"
    auto-select-first
    clearable
    variant="outlined"
    :item-height="52"
  >
    <template #selection="{ item }">
      <DefiIcon :item="item" />
    </template>
    <template #item="{ item }">
      <DefiIcon :item="item" />
    </template>
  </RuiAutoComplete>
</template>
