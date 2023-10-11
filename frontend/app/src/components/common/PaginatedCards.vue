<script setup lang="ts">
type GetKey = (item: any) => string;

const props = defineProps<{
  items: any[];
  identifier: GetKey;
}>();

const { items } = toRefs(props);
const { name: breakpoint } = useDisplay();
const page = ref(1);
const itemsPerPage = computed(() => {
  if (get(breakpoint) === 'xs') {
    return 1;
  } else if (['sm', 'lg', 'md'].includes(get(breakpoint))) {
    return 4;
  }
  return 6;
});

const pages = computed(() => Math.ceil(get(items).length / get(itemsPerPage)));

const visible = computed(() => {
  const start = (get(page) - 1) * get(itemsPerPage);
  return get(items).slice(start, start + get(itemsPerPage));
});

watch(items, () => set(page, 1));
</script>

<template>
  <div>
    <VPagination v-if="pages > 1" v-model="page" :length="pages" />
    <div class="grid md:grid-cols-2 2xl:grid-cols-3 gap-4">
      <div v-for="item in visible" :key="identifier(item)">
        <slot name="item" :item="item" />
      </div>
    </div>
  </div>
</template>
