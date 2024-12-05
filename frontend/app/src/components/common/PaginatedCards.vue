<script setup lang="ts">
import { type TablePaginationData, useBreakpoint } from '@rotki/ui-library';

type GetKey = (item: any) => string;

const props = defineProps<{
  items: any[];
  identifier: GetKey;
}>();

const { items } = toRefs(props);
const { isXlAndDown, isXs } = useBreakpoint();
const page = ref(1);
const itemsPerPage = ref(8);

const firstLimit = computed(() => {
  if (get(isXs))
    return 1;
  else if (get(isXlAndDown))
    return 4;

  return 6;
});

const limits = computed(() => {
  const first = get(firstLimit);
  return [first, first * 2, first * 4];
});

const paginationData = computed({
  get() {
    return {
      limit: get(itemsPerPage),
      limits: get(limits),
      page: get(page),
      total: get(items).length,
    };
  },
  set(value: TablePaginationData) {
    set(page, value.page);
    set(itemsPerPage, value.limit);
  },
});

const visible = computed(() => {
  const start = (get(page) - 1) * get(itemsPerPage);
  return get(items).slice(start, start + get(itemsPerPage));
});

watchImmediate(firstLimit, () => {
  set(itemsPerPage, get(firstLimit));
});

watch([items, firstLimit], () => set(page, 1));
</script>

<template>
  <RuiCard>
    <div class="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4">
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

    <RuiCard
      variant="outlined"
      class="mt-4"
      no-padding
    >
      <RuiTablePagination v-model="paginationData" />
    </RuiCard>
  </RuiCard>
</template>
