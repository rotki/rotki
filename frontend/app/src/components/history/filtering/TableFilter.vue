<template>
  <v-combobox
    :value="selection"
    outlined
    dense
    chips
    small-chips
    deletable-chips
    multiple
    clearable
    prepend-inner-icon="mdi-filter-variant"
    :search-input.sync="search"
    @input="searchUpdated($event)"
    @update:search-input="onSearch($event)"
  >
    <template #no-data>
      <no-filter-available
        :matchers="matchers"
        :used="usedKeys"
        :suggestion="suggestion"
        @click="appendToSearch($event)"
      />
    </template>
  </v-combobox>
</template>

<script lang="ts">
import { computed, defineComponent, PropType, ref } from '@vue/composition-api';
import NoFilterAvailable from '@/components/history/filtering/NoFilterAvailable.vue';
import {
  MatchedKeyword,
  SearchMatcher
} from '@/components/history/filtering/types';
import { assert } from '@/utils/assertions';

export default defineComponent({
  name: 'TableFilter',
  components: { NoFilterAvailable },
  props: {
    matchers: {
      required: true,
      type: Array as PropType<SearchMatcher<any>[]>
    }
  },
  emits: {
    'update:matches'(matches: MatchedKeyword<any>) {
      return !!matches;
    }
  },
  setup(props, { emit }) {
    const selection = ref<string[]>([]);
    const search = ref('');
    const validKeys = props.matchers.map(({ key }) => key);
    const suggestion = computed(() =>
      validKeys.find(value => value.startsWith(search.value))
    );
    const usedKeys = computed(() =>
      selection.value.map(
        entry => entry.split(':').map(value => value.trim())[0]
      )
    );
    const searchUpdated = (selected: string[]) => {
      const strings: string[] = [...selection.value].filter(value =>
        selected.includes(value)
      );
      const matched: Partial<MatchedKeyword<any>> = {};
      for (const entry of selected) {
        const trimmed = entry.trim();
        if (!trimmed) {
          continue;
        }
        const filter = entry.split(':').map(value => value.trim());
        const searchKey = filter[0];
        const keyword = filter[1];

        if (!keyword) {
          continue;
        }

        const fullMatch = validKeys.find(key => searchKey === key);
        if (!fullMatch) {
          console.log(`didn't match ${entry}`);
          continue;
        }

        const matcher = props.matchers.find(value => value.key === searchKey);
        assert(matcher);

        matched[matcher.matchingProperty] = filter[1].trim();
        if (usedKeys.value.includes(searchKey)) {
          const index = strings.findIndex(
            value => value.split(':').map(text => text.trim())[0] === searchKey
          );
          strings[index] = entry;
        } else {
          strings.push(entry);
        }
      }

      selection.value = strings;
      emit('update:matches', matched);
    };
    const appendToSearch = (key: string) => {
      const filter = `${key}:`;
      if (search.value) {
        search.value += ` ${filter}`;
      } else {
        search.value = filter;
      }
    };
    const onSearch = (key: string) => {
      console.log(key);
    };
    return {
      search,
      selection,
      usedKeys,
      suggestion,
      onSearch,
      searchUpdated,
      appendToSearch
    };
  }
});
</script>
