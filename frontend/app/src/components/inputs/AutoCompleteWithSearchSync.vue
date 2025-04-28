<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const model = defineModel<string>({
  required: true,
  set(value) {
    return value === undefined ? '' : value;
  },
});

const props = defineProps<{
  items: string[];
}>();

const { items } = toRefs(props);

const search = ref<string>('');

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
      v-for="(_, name, index) in ($slots as {})"
      #[name]="scope"
      :key="index"
    >
      <slot
        v-bind="{ scope }"
        :name="name"
      />
    </template>
  </RuiAutoComplete>
</template>
