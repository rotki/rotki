<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library-compat';

type GetKey = (item: any) => string;

const props = defineProps<{
  items: any[];
  identifier: GetKey;
}>();

const { items } = toRefs(props);
const { isXs, isXlAndDown } = useBreakpoint();
const page = ref(1);
const itemsPerPage = computed(() => {
  if (get(isXs))
    return 1;
  else if (get(isXlAndDown))
    return 4;

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
    <VPagination
      v-if="pages > 1"
      v-model="page"
      :length="pages"
      class="mb-4"
    />
    <div class="grid md:grid-cols-2 2xl:grid-cols-3 gap-4">
      <div
        v-for="item in visible"
        :key="identifier(item)"
      >
        <slot
          name="item"
          :item="item"
        />
      </div>
    </div>
  </div>
</template>
