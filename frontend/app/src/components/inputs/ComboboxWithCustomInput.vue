<script setup lang="ts">
import { type ComputedRef, type Ref, useListeners } from 'vue';

const props = withDefaults(
  defineProps<{
    value?: string | null;
    items: any[];
  }>(),
  {
    value: ''
  }
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
}>();

const input = (value: string) => {
  emit('input', value);
};

const { items } = toRefs(props);

const search: Ref<string | null> = ref('');

watch(search, search => {
  if (search === null) {
    search = '';
  }
  input(search);
});

const filteredItems: ComputedRef<any[]> = computed(() => {
  const suggestions = get(items);
  const searchVal = get(search);
  if (!searchVal) {
    return suggestions;
  }
  return suggestions.filter(suggestion => suggestion.includes(searchVal));
});

const rootAttrs = useAttrs();
const rootListeners = useListeners();
const slots = useSlots();
</script>

<template>
  <v-combobox
    :value="value"
    v-bind="rootAttrs"
    :search-input.sync="search"
    :items="filteredItems"
    v-on="rootListeners"
    @input="input($event)"
  >
    <!-- Pass on all named slots -->
    <slot v-for="slot in Object.keys(slots)" :slot="slot" :name="slot" />

    <!-- Pass on all scoped slots -->
    <template v-for="slot in Object.keys($scopedSlots)" #[slot]="scope">
      <slot v-bind="scope" :name="slot" />
    </template>
  </v-combobox>
</template>
