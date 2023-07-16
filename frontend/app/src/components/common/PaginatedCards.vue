<script setup lang="ts">
import { type PropType } from 'vue';

type GetKey = (item: any) => string;

const props = defineProps({
  items: {
    required: true,
    type: Array as PropType<any[]>
  },
  identifier: {
    required: true,
    type: Function as PropType<GetKey>
  }
});

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
    <VRow class="mt-2">
      <VCol
        v-for="item in visible"
        :key="identifier(item)"
        cols="12"
        md="6"
        lg="6"
        xl="4"
      >
        <slot name="item" :item="item" />
      </VCol>
    </VRow>
  </div>
</template>
