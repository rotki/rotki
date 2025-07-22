<script setup lang="ts">
import type {
  MatchedKeyword,
  MatchedKeywordWithBehaviour,
  SavedFilterLocation,
  SearchMatcher,
  Suggestion,
} from '@/types/filtering';
import { assert, type AssetInfo, getTextToken } from '@rotki/common';
import FilterDropdown from '@/components/table-filter/FilterDropdown.vue';
import SavedFilterManagement from '@/components/table-filter/SavedFilterManagement.vue';
import SuggestedItem from '@/components/table-filter/SuggestedItem.vue';
import { compareTextByKeyword } from '@/utils/assets';
import { logger } from '@/utils/logging';
import { splitSearch } from '@/utils/search';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<{
  matches: MatchedKeywordWithBehaviour<any>;
  matchers: SearchMatcher<any, any>[];
  location?: SavedFilterLocation;
  disabled?: boolean;
}>(), {
  disabled: false,
  location: undefined,
});

const emit = defineEmits<{
  (e: 'update:matches', matches: MatchedKeywordWithBehaviour<any>): void;
}>();

defineSlots<{
  tooltip: () => any;
}>();

const { matchers, matches } = toRefs(props);

const input = ref();
const selection = ref<Suggestion[]>([]);

const search = ref('');
const selectedSuggestion = ref(0);
const suggestedFilter = ref<Suggestion>({
  asset: false,
  index: 0,
  key: '',
  total: 0,
  value: '',
});
const validKeys = computed(() => get(matchers).map(({ key }) => key));

const selectedMatcher = computed(() => {
  const searchKey = splitSearch(get(search));

  // If searchKey.exclude is not defined it means user hasn't put any matcher symbol
  // So we shouldn't set the selectedMatcher yet.
  if (searchKey.exclude === undefined)
    return undefined;

  const key = get(validKeys).find(value => value === searchKey.key);
  return matcherForKey(key) ?? undefined;
});

const usedKeys = computed(() => get(selection).map(entry => entry.key));

const suggestionBeingEdited = ref<Suggestion>();

function isSuggestionBeingEdited(suggestion: Suggestion) {
  const edited = get(suggestionBeingEdited);
  if (!edited)
    return false;

  return getSuggestionText(suggestion).text === getSuggestionText(edited).text;
}

function clickItem(item: Suggestion) {
  if (typeof item.value !== 'boolean') {
    set(suggestionBeingEdited, item);
    set(search, `${item.key}${item.exclude ? '!=' : '='}`);
  }
}

function cancelEditSuggestion() {
  set(suggestionBeingEdited, undefined);
  set(search, '');
}

function updateEditSuggestionSearch(value: string) {
  const beingEdited = get(suggestionBeingEdited);
  if (!beingEdited)
    return;

  set(search, `${beingEdited.key}${beingEdited.exclude ? '!=' : '='}${value}`);
}

function matcherForKey(searchKey: string | undefined) {
  return get(matchers).find(({ key }) => key === searchKey);
}

function matcherForKeyValue(searchKey: string | undefined) {
  return get(matchers).find(({ keyValue }) => keyValue === searchKey);
}

function setSearchToMatcherKey(matcher: SearchMatcher<any>) {
  const boolean = 'boolean' in matcher;
  if (boolean) {
    applyFilter({
      asset: false,
      index: 0,
      key: matcher.key,
      total: 1,
      value: true,
    });
    return;
  }
  const filter = `${matcher.key}=`;
  set(search, filter);
  get(input)?.focus?.();
}

function updateMatches(pairs: Suggestion[]) {
  const matched: Partial<MatchedKeyword<any>> = {};
  const validPairs: Suggestion[] = [];

  for (const entry of pairs) {
    const key = entry.key;
    const matcher = matcherForKey(key);
    if (!matcher)
      continue;

    const valueKey = (matcher.keyValue || matcher.key) as string;
    let transformedKeyword: string | boolean = '';

    if ('string' in matcher) {
      if (typeof entry.value !== 'string')
        continue;

      if (matcher.validate(entry.value)) {
        transformedKeyword = matcher.serializer?.(entry.value) || entry.value;

        if (entry.exclude)
          transformedKeyword = `!${transformedKeyword}`;
      }
      else {
        continue;
      }
    }
    else if ('asset' in matcher) {
      transformedKeyword = typeof entry.value !== 'string' ? entry.value.identifier : entry.value;
    }
    else {
      transformedKeyword = true;
    }

    if (!transformedKeyword)
      continue;

    validPairs.push(entry);

    if (matcher.multiple) {
      if (!matched[valueKey])
        matched[valueKey] = [];

      (matched[valueKey] as (string | boolean)[]).push(transformedKeyword);
    }
    else {
      matched[valueKey] = transformedKeyword;
    }
  }

  set(selection, validPairs);
  emit('update:matches', matched);
}

function findBeingSelectedIndex(selection: Suggestion[]) {
  return selection.findIndex(sel => isSuggestionBeingEdited(sel));
}

function applyFilter(filter: Suggestion) {
  let newSelection = [...get(selection)];
  const key = filter.key;
  const index = newSelection.findIndex(value => value.key === key);
  const matcher = matcherForKey(key);
  assert(matcher);

  if (index >= 0 && (!matcher.multiple || newSelection[index].exclude !== filter.exclude))
    newSelection = newSelection.filter(item => item.key !== key);

  let beingEditedIndex = -1;

  const beingEdited = get(suggestionBeingEdited);
  if (beingEdited) {
    beingEditedIndex = findBeingSelectedIndex(newSelection);
    if (beingEditedIndex > -1) {
      newSelection.splice(beingEditedIndex, 1);
    }
    set(suggestionBeingEdited, undefined);
  }

  if (beingEditedIndex === -1) {
    newSelection.push(filter);
  }
  else {
    newSelection.splice(beingEditedIndex, 0, filter);
  }

  updateMatches(newSelection);
  set(search, '');
}

const filteredMatchers = computed<SearchMatcher<any>[]>(() => {
  const filteredByUsedKeys = get(matchers).filter(({ key, multiple }) => !get(usedKeys).includes(key) || multiple);

  const searchVal = get(search);
  if (!searchVal)
    return filteredByUsedKeys;

  const searchToken = getTextToken(searchVal);
  return filteredByUsedKeys
    .filter(({ key }) => getTextToken(key).includes(searchToken))
    .sort((a, b) => compareTextByKeyword(getTextToken(a.key), getTextToken(b.key), searchToken));
});

async function applySuggestion() {
  const selectedIndex = get(selectedSuggestion);
  if (!get(selectedMatcher)) {
    const filteredMatchersVal = get(filteredMatchers);

    if (filteredMatchersVal.length > selectedIndex)
      setSearchToMatcherKey(filteredMatchersVal[selectedIndex]);

    return;
  }

  const filter = get(suggestedFilter);
  if (filter.value) {
    await nextTick(() => applyFilter(filter));
  }
  else {
    const { exclude, key, value: keyword } = splitSearch(get(search));

    const matcher = matcherForKey(key);
    let asset = false;
    if (matcher) {
      let suggestedItems: (AssetInfo | string)[] = [];
      if ('string' in matcher) {
        suggestedItems = matcher.suggestions();
      }
      else if ('asset' in matcher) {
        suggestedItems = await matcher.suggestions(keyword);
        asset = true;
      }
      else if (!('boolean' in matcher)) {
        logger.debug('Matcher doesn\'t have asset=true, string=true, or boolean=true.', selectedMatcher);
      }

      if (suggestedItems.length === 0 && 'validate' in matcher && matcher.validate(keyword)) {
        await nextTick(() =>
          applyFilter({
            asset,
            exclude,
            index: 0,
            key,
            total: 1,
            value: keyword,
          }),
        );
      }
      else {
        set(suggestionBeingEdited, undefined);
      }
    }
    if (!key)
      get(input).blur();
  }
  set(selectedSuggestion, 0);
  set(search, '');
}

onMounted(() => {
  get(input).onTabDown = function (e: KeyboardEvent) {
    e.preventDefault();
    e.stopPropagation();
    moveSuggestion(false);
  };
  get(input).onEnterDown = function (e: KeyboardEvent) {
    e.preventDefault();
    e.stopPropagation();
  };
});

watch(search, () => {
  set(selectedSuggestion, 0);
});

function moveSuggestion(up: boolean) {
  const total = get(selectedMatcher) ? get(suggestedFilter).total : get(filteredMatchers).length;

  let position = get(selectedSuggestion);
  const move = up ? -1 : 1;

  position += move;

  if (position >= total)
    set(selectedSuggestion, 0);
  else if (position < 0)
    set(selectedSuggestion, total - 1);
  else set(selectedSuggestion, position);
}

// TODO: This is too specific for custom asset, move it!
function getDisplayValue(suggestion: Suggestion) {
  const value = suggestion.value;
  if (typeof value === 'string')
    return value;

  return value.isCustomAsset ? value.name : value.symbol;
}

function getSuggestionText(suggestion: Suggestion) {
  const operator = suggestion.exclude ? '!=' : '=';
  const startSelection = suggestion.key.length + operator.length;
  const value = getDisplayValue(suggestion);
  return {
    endSelection: startSelection + value.length,
    startSelection,
    text: `${suggestion.key}${operator}${value}`,
  };
}

function restoreSelection(matches: MatchedKeywordWithBehaviour<any>): void {
  const oldSelection = get(selection);
  const newSelection: Suggestion[] = [];
  Object.entries(matches).forEach(([key, value]) => {
    const foundMatchers = matcherForKeyValue(key);

    if (!(foundMatchers && value))
      return;

    const values = Array.isArray(value) ? value : [value];
    const asset = 'asset' in foundMatchers;
    const boolean = 'boolean' in foundMatchers;

    values.forEach((value) => {
      let deserializedValue = null;
      if (asset) {
        const prevAssetSelection = oldSelection.find(({ key }) => key === foundMatchers.key);
        if (prevAssetSelection)
          deserializedValue = prevAssetSelection.value;
      }

      let exclude = false;
      if (!deserializedValue) {
        if (boolean || typeof value === 'boolean') {
          deserializedValue = true;
        }
        else if (typeof value === 'string') {
          let normalizedValue = value;
          if (!asset && value.startsWith('!')) {
            normalizedValue = value.substring(1);
            exclude = true;
          }
          deserializedValue = foundMatchers.deserializer?.(normalizedValue) || normalizedValue;
        }
      }

      newSelection.push({
        asset,
        exclude,
        index: 0,
        key: foundMatchers.key,
        total: 1,
        value: deserializedValue,
      });
    });
  });

  set(selection, newSelection);
}

onMounted(() => {
  restoreSelection(get(matches));
});

watch(matches, (matches) => {
  restoreSelection(matches);
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :disabled="!disabled || !$slots.tooltip"
    :open-delay="400"
    :close-delay="1000"
    class="block flex-1 max-w-full"
    tooltip-class="max-w-[12rem]"
  >
    <template #activator>
      <div
        class="flex items-center gap-2"
        data-cy="table-filter"
      >
        <RuiAutoComplete
          ref="input"
          v-model:search-input="search"
          :model-value="selection"
          :class="{
            '[&_input:not(.edit-input)]:hidden': !!suggestionBeingEdited,
          }"
          variant="outlined"
          dense
          :disabled="disabled"
          :label="t('table_filter.label')"
          clearable
          hide-details
          custom-value
          hide-custom-value
          :options="[]"
          return-object
          disable-interaction
          v-bind="$attrs"
          @update:model-value="updateMatches($event)"
          @keydown.enter="applySuggestion()"
          @keydown.up.prevent="moveSuggestion(true)"
          @keydown.down.prevent="moveSuggestion(false)"
        >
          <template #selection="{ item, chipAttrs }">
            <RuiChip
              tile
              size="sm"
              class="font-medium !py-0"
              clickable
              closeable
              v-bind="chipAttrs"
              @click="clickItem(item)"
            >
              <SuggestedItem
                chip
                :edit-mode="isSuggestionBeingEdited(item)"
                :suggestion="item"
                @cancel-edit="cancelEditSuggestion()"
                @update:search="updateEditSuggestionSearch($event)"
              />
            </RuiChip>
          </template>
          <template #no-data>
            <FilterDropdown
              :matches="matches"
              :matchers="filteredMatchers"
              :keyword="search"
              :selected-matcher="selectedMatcher"
              :selected-suggestion="selectedSuggestion"
              @apply-filter="applyFilter($event)"
              @suggest="suggestedFilter = $event"
              @click="setSearchToMatcherKey($event)"
            />
          </template>
        </RuiAutoComplete>

        <SavedFilterManagement
          v-if="location"
          :disabled="disabled"
          :selection="selection"
          :location="location"
          :matchers="matchers"
          @update:matches="updateMatches($event)"
        />
      </div>
    </template>
    <slot name="tooltip" />
  </RuiTooltip>
</template>
