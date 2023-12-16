<script setup lang="ts">
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

const search = ref<string>();

watch(search, (search) => {
  if (search === undefined)
    search = '';

  set(model, search);
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    v-bind="$attrs"
    v-model:search-input="search"
    :options="items"
    variant="outlined"
    custom-value
  >
    <!-- Pass on all named slots -->
    <template
      v-for="(_, name) in $slots"
      #[name]="scope"
    >
      <slot
        v-bind="scope"
        :name="name"
      />
    </template>
  </RuiAutoComplete>
</template>
