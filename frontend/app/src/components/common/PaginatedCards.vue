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
      if (breakpoint.value === 'xs') {
        return 1;
      } else if (['sm', 'lg', 'md'].includes(breakpoint.value)) {
        return 4;
      }
      return 6;
    });

    const pages = computed(() => {
      return Math.ceil(items.value.length / itemsPerPage.value);
    });

    const visible = computed(() => {
      const start = (page.value - 1) * itemsPerPage.value;
      return items.value.slice(start, start + itemsPerPage.value);
    });

    watch(items, () => (page.value = 1));

    return {
      page,
      pages,
      visible
    };
  }
});
</script>
