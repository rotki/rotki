<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    value?: string | null;
    items: any[];
  }>(),
  {
    value: '',
  },
);

const emit = defineEmits<{
  (e: 'input', value: string): void;
}>();

function input(value: string) {
  emit('input', value);
}

const { items } = toRefs(props);

const search: Ref<string | undefined> = ref('');

watch(search, (search) => {
  if (search === undefined)
    search = '';

  input(search);
});

const rootAttrs = useAttrs();
const slots = useSlots();
</script>

<template>
  <RuiAutoComplete
    :value="value"
    v-bind="rootAttrs"
    :search-input.sync="search"
    :options="items"
    variant="outlined"
    custom-value
    v-on="
      // eslint-disable-next-line vue/no-deprecated-dollar-listeners-api
      $listeners
    "
    @input="input($event)"
  >
    <!-- Pass on all named slots -->
    <slot
      v-for="slot in Object.keys(slots)"
      :slot="slot"
      :name="slot"
    />

    <!-- Pass on all scoped slots -->
    <template
      v-for="slot in Object.keys($scopedSlots)"
      #[slot]="scope"
    >
      <slot
        v-bind="scope"
        :name="slot"
      />
    </template>
  </RuiAutoComplete>
</template>
