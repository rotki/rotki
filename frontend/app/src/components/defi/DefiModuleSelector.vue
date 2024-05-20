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
    value?: string;
    items?: Module[];
  }>(),
  {
    value: '',
    items: () => [],
  },
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
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
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
  >
    <template #selection="{ item }">
      <DefiIcon :item="item" />
    </template>
    <template #item="{ item }">
      <DefiIcon :item="item" />
    </template>
  </RuiAutoComplete>
</template>
