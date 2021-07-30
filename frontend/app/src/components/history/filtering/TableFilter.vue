<template>
  <v-combobox
    ref="input"
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
    @keydown.enter="applySuggestion"
  >
    <template #no-data>
      <no-filter-available
        :matchers="matchers"
        :used="usedKeys"
        :keyword="search"
        :suggestion="suggestion"
        :selected-suggestion="selectedSuggestion"
        @apply:filter="applyFilter($event)"
        @suggest="suggestedFilter = $event"
        @click="appendToSearch($event)"
      />
    </template>
  </v-combobox>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  nextTick,
  onMounted,
  PropType,
  ref,
  watch
} from '@vue/composition-api';
import NoFilterAvailable from '@/components/history/filtering/NoFilterAvailable.vue';
import {
  MatchedKeyword,
  SearchMatcher,
  Suggestion
} from '@/components/history/filtering/types';
import { splitSearch } from '@/components/history/filtering/utils';
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
    const input = ref();
    const selection = ref<string[]>([]);
    const search = ref('');
    const validKeys = props.matchers.map(({ key }) => key);
    const suggestion = computed(() => {
      const searchKey = splitSearch(search.value);
      const key = validKeys.find(value => value.startsWith(searchKey[0]));
      return props.matchers.find(matcher => matcher.key === key) ?? null;
    });
    const usedKeys = computed(() =>
      selection.value.map(entry => splitSearch(entry)[0])
    );
    const searchUpdated = (selected: string[]) => {
      const strings: string[] = [...selection.value].filter(
        value =>
          selected.includes(value) ||
          selected.find(selection => value.startsWith(selection))
      );
      const matched: Partial<MatchedKeyword<any>> = {};
      for (const entry of selected) {
        const trimmed = entry.trim();
        if (!trimmed) {
          continue;
        }
        const filter = splitSearch(entry);
        const searchKey = filter[0];
        const keyword = filter[1];

        if (!keyword) {
          continue;
        }

        const fullMatch = validKeys.find(key => searchKey === key);
        if (!fullMatch) {
          continue;
        }

        const matcher = props.matchers.find(value => value.key === searchKey);
        assert(matcher);

        matched[matcher.matchingProperty] = filter[1].trim();
        const searchTerm = `${searchKey}: ${keyword}`;
        if (usedKeys.value.includes(searchKey)) {
          const index = strings.findIndex(
            value => splitSearch(value)[0] === searchKey
          );
          strings[index] = searchTerm;
        } else {
          strings.push(searchTerm);
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
      input.value.focus();
    };

    const applyFilter = (filter: string) => {
      const newSelection = [...selection.value];
      const splitFilter = splitSearch(filter);
      const index = newSelection.findIndex(
        value => splitSearch(value)[0] === splitFilter[0]
      );

      if (index >= 0) {
        newSelection[index] = filter;
      } else {
        newSelection.push(filter);
      }

      selection.value = newSelection;

      const matched: Partial<MatchedKeyword<any>> = {};

      for (const entry of selection.value) {
        const entryFilter = splitSearch(entry);
        const searchKey = entryFilter[0];
        const matcher = props.matchers.find(value => value.key === searchKey);
        assert(matcher);
        matched[matcher.matchingProperty] = entryFilter[1].trim();
      }

      emit('update:matches', matched);
    };

    const selectedSuggestion = ref(0);
    const suggestedFilter = ref<Suggestion>({
      index: 0,
      total: 0,
      suggestion: ''
    });
    const applySuggestion = () => {
      const filter = suggestedFilter.value;
      const suggestion = filter.suggestion;
      if (suggestion.length > 0) {
        nextTick(() => {
          applyFilter(suggestion);
        });
      }
      selectedSuggestion.value = 0;
    };

    onMounted(() => {
      input.value.onTabDown = function (e: KeyboardEvent) {
        e.preventDefault();
        e.stopPropagation();
        if (selectedSuggestion.value < suggestedFilter.value.total - 1) {
          selectedSuggestion.value += 1;
        } else {
          selectedSuggestion.value = 0;
        }
      };
    });

    watch(search, () => {
      selectedSuggestion.value = 0;
    });

    return {
      search,
      selection,
      usedKeys,
      suggestion,
      suggestedFilter,
      selectedSuggestion,
      searchUpdated,
      appendToSearch,
      applyFilter,
      applySuggestion,
      input
    };
  }
});
</script>
