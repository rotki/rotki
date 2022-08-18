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
import { get, set } from '@vueuse/core';
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
      type: Array as PropType<SearchMatcher<any, any>[]>
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
      return get(matchers).find(({ key }) => key === searchKey);
    };

    const suggestion = computed(() => {
      const searchKey = splitSearch(get(search));
      const key = validKeys.find(value => value.startsWith(searchKey[0]));
      return matcherForKey(key) ?? null;
    });

    const usedKeys = computed(() =>
      get(selection).map(entry => splitSearch(entry)[0])
    );

    const onSelectionUpdate = (pairs: string[]) => {
      updateMatches(pairs);
    };

    const appendToSearch = (key: string) => {
      const filter = `${key}:`;
      if (get(search)) {
        search.value += ` ${filter}`;
      } else {
        set(search, filter);
      }
      get(input).focus();
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
          const valueKey = (matcher.keyValue || matcher.key) as string;
          const transformedKeyword = matcher.transformer?.(keyword) || keyword;

          if (matcher.multiple) {
            if (!matched[valueKey]) {
              matched[valueKey] = [];
            }
            (matched[valueKey] as string[]).push(transformedKeyword);
          } else {
            matched[valueKey] = transformedKeyword;
          }
        }
      }

      set(selection, validPairs);
      emit('update:matches', matched);
    }

    const applyFilter = (filter: string) => {
      const newSelection = [...get(selection)];
      const [key] = splitSearch(filter);
      const index = newSelection.findIndex(
        value => splitSearch(value)[0] === key
      );
      const matcher = matcherForKey(key);
      assert(matcher);

      if (index >= 0 && !matcher.multiple) {
        newSelection[index] = filter;
      } else {
        newSelection.push(filter);
      }

      updateMatches(newSelection);
      set(search, '');
    };

    const selectedSuggestion = ref(0);
    const suggestedFilter = ref<Suggestion>({
      index: 0,
      total: 0,
      suggestion: ''
    });
    const applySuggestion = () => {
      const filter = get(suggestedFilter);
      const suggestion = filter.suggestion;
      if (suggestion.length > 0) {
        nextTick(() => {
          applyFilter(suggestion);
        });
      } else {
        const [key, keyword] = splitSearch(get(search));
        const matcher = matcherForKey(key);
        if (matcher && matcher.suggestions().length === 0) {
          if (matcher.validate(keyword)) {
            nextTick(() => applyFilter(`${key}: ${keyword}`));
          }
        }
        if (!key) {
          get(input).blur();
        }
      }
      set(selectedSuggestion, 0);
      set(search, '');
    };

    onMounted(() => {
      get(input).onTabDown = function (e: KeyboardEvent) {
        e.preventDefault();
        e.stopPropagation();
        if (get(selectedSuggestion) < get(suggestedFilter).total - 1) {
          selectedSuggestion.value += 1;
        } else {
          set(selectedSuggestion, 0);
        }
      };
      get(input).onEnterDown = function (e: KeyboardEvent) {
        e.preventDefault();
        e.stopPropagation();
      };
    });

    watch(search, () => {
      set(selectedSuggestion, 0);
    });

    const moveSuggestion = (up: boolean) => {
      let position = get(selectedSuggestion);
      const move = up ? -1 : 1;

      position += move;

      if (position >= get(suggestedFilter).total) {
        set(selectedSuggestion, 0);
      } else if (position < 0) {
        set(selectedSuggestion, get(suggestedFilter).total - 1);
      } else {
        set(selectedSuggestion, position);
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
