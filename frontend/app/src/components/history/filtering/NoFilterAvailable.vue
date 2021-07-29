<template>
  <div class="pa-4">
    <div class="caption-text text--secondary">Available filters</div>
    <v-divider class="my-2" />
    <filter-entry
      v-for="matcher in available"
      :key="matcher.key"
      :matcher="matcher"
      @click="click($event)"
    />
  </div>
</template>

<script lang="ts">
import { computed, defineComponent, PropType } from '@vue/composition-api';
import FilterEntry from '@/components/history/filtering/FilterEntry.vue';
import { SearchMatcher } from '@/components/history/filtering/types';

export default defineComponent({
  name: 'NoFilterAvailable',
  components: { FilterEntry },
  props: {
    matchers: {
      required: true,
      type: Array as PropType<SearchMatcher<any>[]>
    },
    used: {
      required: true,
      type: Array as PropType<string[]>
    }
  },
  emits: {
    click: (key: string) => {
      return key.trim().length > 0;
    }
  },
  setup(props, { emit }) {
    const available = computed<SearchMatcher<any>[]>(
      ({
        matchers,
        used
      }: {
        matchers: SearchMatcher<any>[];
        used: string[];
      }) => matchers.filter(({ key }) => !used.includes(key))
    );
    const click = (key: string) => {
      emit('click', key);
    };
    return {
      click,
      available
    };
  }
});
</script>
