<template>
  <div>
    <v-pagination v-if="pages > 1" v-model="page" :length="pages" />
    <v-row class="mt-2">
      <v-col
        v-for="item in visible"
        :key="identifier(item)"
        cols="12"
        sm="6"
        lg="6"
        xl="4"
      >
        <slot name="item" :item="item" />
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { setupThemeCheck } from '@/composables/common';

type GetKey = (item: any) => string;

export default defineComponent({
  name: 'PaginatedCards',
  props: {
    items: {
      required: true,
      type: Array
    },
    identifier: {
      required: true,
      type: Function as PropType<GetKey>
    }
  },
  setup(props) {
    const { items } = toRefs(props);
    const { breakpoint } = setupThemeCheck();
    const page = ref(1);
    const itemsPerPage = computed(() => {
      if (get(breakpoint) === 'xs') {
        return 1;
      } else if (['sm', 'lg', 'md'].includes(get(breakpoint))) {
        return 4;
      }
      return 6;
    });

    const pages = computed(() => {
      return Math.ceil(get(items).length / get(itemsPerPage));
    });

    const visible = computed(() => {
      const start = (get(page) - 1) * get(itemsPerPage);
      return get(items).slice(start, start + get(itemsPerPage));
    });

    watch(items, () => set(page, 1));

    return {
      page,
      pages,
      visible
    };
  }
});
</script>
