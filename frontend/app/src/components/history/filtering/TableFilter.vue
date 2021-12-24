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
    hide-details
    prepend-inner-icon="mdi-filter-variant"
    :search-input.sync="search"
    @input="onSelectionUpdate($event)"
    @keydown.enter="applySuggestion"
    @keydown.up.prevent
    @keydown.up="moveSuggestion(true)"
    @keydown.down.prevent
    @keydown.down="moveSuggestion(false)"
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
  toRefs,
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

    const { matchers } = toRefs(props);

    const matcherForKey = (searchKey: string | undefined) => {
      return matchers.value.find(({ key }) => key === searchKey);
    };

    const suggestion = computed(() => {
      const searchKey = splitSearch(search.value);
      const key = validKeys.find(value => value.startsWith(searchKey[0]));
      return matcherForKey(key) ?? null;
    });
    const usedKeys = computed(() =>
      selection.value.map(entry => splitSearch(entry)[0])
    );

    const onSelectionUpdate = (pairs: string[]) => {
      updateMatches(pairs);
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

    function updateMatches(pairs: string[]) {
      const matched: Partial<MatchedKeyword<any>> = {};
      const validPairs: string[] = [];
      for (const entry of pairs) {
        const [key, keyword] = splitSearch(entry);
        const matcher = matcherForKey(key);
        assert(matcher);

        if (matcher.validate(keyword)) {
          validPairs.push(entry);
          const valueKey = (matcher.keyValue ?? matcher.key) as string;
          matched[valueKey] = matcher.transformer?.(keyword) ?? keyword;
        }
      }

      selection.value = validPairs;

      emit('update:matches', matched);
    }

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

      updateMatches(newSelection);
      search.value = '';
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
      } else {
        const [key, keyword] = splitSearch(search.value);
        const matcher = matcherForKey(key);
        if (matcher && matcher.suggestions().length === 0) {
          if (matcher.validate(keyword)) {
            nextTick(() => applyFilter(`${key}: ${keyword}`));
          }
        }
        if (!key) {
          input.value.blur();
        }
      }
      selectedSuggestion.value = 0;
      search.value = '';
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
      input.value.onEnterDown = function (e: KeyboardEvent) {
        e.preventDefault();
        e.stopPropagation();
      };
    });

    watch(search, () => {
      selectedSuggestion.value = 0;
    });

    const moveSuggestion = (up: boolean) => {
      let position = selectedSuggestion.value;
      const move = up ? -1 : 1;

      position += move;

      if (position >= suggestedFilter.value.total) {
        selectedSuggestion.value = 0;
      } else if (position < 0) {
        selectedSuggestion.value = suggestedFilter.value.total - 1;
      } else {
        selectedSuggestion.value = position;
      }
    };

    return {
      search,
      selection,
      usedKeys,
      suggestion,
      suggestedFilter,
      selectedSuggestion,
      onSelectionUpdate,
      appendToSearch,
      applyFilter,
      applySuggestion,
      moveSuggestion,
      input
    };
  }
});
</script>
