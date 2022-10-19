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
    <template #selection="{ item, selected }">
      <v-chip
        label
        small
        class="font-weight-medium"
        :input-value="selected"
        close
        @click:close="removeSelection(item)"
        @click="
          removeSelection(item);
          selectItem(item);
        "
      >
        <suggested-item :suggestion="item" />
      </v-chip>
    </template>
    <template #no-data>
      <no-filter-available
        :matchers="matchers"
        :used="usedKeys"
        :keyword="search"
        :suggestion="searchSuggestion"
        :selected-suggestion="selectedSuggestion"
        @apply:filter="applyFilter($event)"
        @suggest="suggestedFilter = $event"
        @click="appendToSearch($event)"
      />
    </template>
  </v-combobox>
</template>

<script setup lang="ts">
import { AssetInfo } from '@rotki/common/lib/data';
import { PropType } from 'vue';
import NoFilterAvailable from '@/components/history/filtering/NoFilterAvailable.vue';
import SuggestedItem from '@/components/history/filtering/SuggestedItem.vue';
import { MatchedKeyword, SearchMatcher, Suggestion } from '@/types/filtering';
import { assert } from '@/utils/assertions';
import { logger } from '@/utils/logging';
import { splitSearch } from '@/utils/search';

const props = defineProps({
  matchers: {
    required: true,
    type: Array as PropType<SearchMatcher<any, any>[]>
  }
});

const emit = defineEmits({
  'update:matches'(matches: MatchedKeyword<any>) {
    return !!matches;
  }
});

const { matchers } = toRefs(props);

const input = ref();
const selection = ref<Suggestion[]>([]);
const search = ref('');
const selectedSuggestion = ref(0);
const suggestedFilter = ref<Suggestion>({
  index: 0,
  total: 0,
  key: '',
  value: ''
});
const validKeys = computed(() => get(matchers).map(({ key }) => key));

const searchSuggestion = computed(() => {
  const searchKey = splitSearch(get(search));
  const key = get(validKeys).find(value => value.startsWith(searchKey[0]));
  return matcherForKey(key) ?? null;
});

const usedKeys = computed(() => get(selection).map(entry => entry.key));

const onSelectionUpdate = (pairs: Suggestion[]) => {
  updateMatches(pairs);
};

const removeSelection = (suggestion: Suggestion) => {
  updateMatches(get(selection).filter(sel => sel !== suggestion));
};

const matcherForKey = (searchKey: string | undefined) => {
  return get(matchers).find(({ key }) => key === searchKey);
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

function updateMatches(pairs: Suggestion[]) {
  const matched: Partial<MatchedKeyword<any>> = {};
  const validPairs: Suggestion[] = [];

  for (const entry of pairs) {
    const key = entry.key;
    const matcher = matcherForKey(key);
    if (!matcher) {
      continue;
    }

    const valueKey = (matcher.keyValue || matcher.key) as string;
    let transformedKeyword: string = '';
    if ('validate' in matcher) {
      if (typeof entry.value !== 'string') {
        continue;
      }
      if (matcher.validate(entry.value)) {
        transformedKeyword = matcher.transformer?.(entry.value) || entry.value;
      } else {
        continue;
      }
    } else if (typeof entry.value !== 'string') {
      transformedKeyword = entry.value.identifier;
    }

    if (!transformedKeyword) {
      continue;
    }

    validPairs.push(entry);

    if (matcher.multiple) {
      if (!matched[valueKey]) {
        matched[valueKey] = [];
      }
      (matched[valueKey] as string[]).push(transformedKeyword);
    } else {
      matched[valueKey] = transformedKeyword;
    }
  }

  set(selection, validPairs);
  emit('update:matches', matched);
}

const applyFilter = (filter: Suggestion) => {
  const newSelection = [...get(selection)];
  const key = filter.key;
  const index = newSelection.findIndex(value => value.key === key);
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

const applySuggestion = async () => {
  const filter = get(suggestedFilter);
  if (filter.value) {
    nextTick(() => applyFilter(filter));
  } else {
    const [key, keyword] = splitSearch(get(search));
    const matcher = matcherForKey(key);
    if (matcher) {
      let suggestedItems: (AssetInfo | string)[] = [];
      if ('string' in matcher) {
        suggestedItems = matcher.suggestions();
      } else if ('asset' in matcher) {
        suggestedItems = await matcher.suggestions(keyword);
      } else {
        logger.debug('Matcher missing asset=true or string=true', matcher);
      }

      if (suggestedItems.length === 0) {
        if ('validate' in matcher && matcher.validate(keyword)) {
          nextTick(() =>
            applyFilter({
              key,
              value: keyword,
              index: 0,
              total: 1
            })
          );
        }
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

// TODO: This is too specific for custom asset, move it!
const getDisplayValue = (suggestion: Suggestion) => {
  let value = suggestion.value;
  if (typeof value === 'string') {
    return value;
  }

  return value.isCustomAsset ? value.name : value.symbol;
};

const getSuggestionText = (suggestion: Suggestion) => {
  return `${suggestion.key}: ${getDisplayValue(suggestion)}`;
};

const selectItem = (suggestion: Suggestion) => {
  nextTick(() => {
    set(search, getSuggestionText(suggestion));
  });
};
</script>
