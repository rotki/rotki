<script setup lang="ts">
import type { ComputedRef, Ref } from 'vue';

defineOptions({
  inheritAttrs: false,
});

const props = defineProps<{
  modelValue: string;
  items: string[];
}>();

const emit = defineEmits<{
  (e: 'update:model-value', value: string): void;
}>();

const model = useSimpleVModel(props, emit);

const { items } = toRefs(props);

const search: Ref<string | null> = ref('');

watch(search, (search) => {
  if (search === null)
    search = '';

  set(model, search);
});

const filteredItems: ComputedRef<string[]> = computed(() => {
  const suggestions = get(items);
  const searchVal = get(search);
  if (!searchVal)
    return suggestions;

  return suggestions.filter(suggestion => suggestion.includes(searchVal));
});
</script>

<template>
  <VCombobox
    v-model="model"
    v-bind="$attrs"
    v-model:search-input="search"
    :items="filteredItems"
  >
    <!-- Pass on all scoped slots -->
    <template
      v-for="(_, name) in $slots"
      #[name]="scope"
    >
      <slot
        v-bind="scope"
        :name="name"
      />
    </template>
  </VCombobox>
</template>
