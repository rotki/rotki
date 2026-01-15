<script setup lang="ts">
import type { AssetInfo } from '@rotki/common';
import type {
  MatchedKeywordWithBehaviour,
  SavedFilterLocation,
  SearchMatcher,
  Suggestion,
} from '@/types/filtering';
import { useChipGrouping } from '@/components/table-filter/composables/use-chip-grouping';
import { useFilterMatchers } from '@/components/table-filter/composables/use-filter-matchers';
import { useFilterSelection } from '@/components/table-filter/composables/use-filter-selection';
import { useMatcherUtils } from '@/components/table-filter/composables/use-matcher-utils';
import FilterDropdown from '@/components/table-filter/FilterDropdown.vue';
import SavedFilterManagement from '@/components/table-filter/SavedFilterManagement.vue';
import SelectionChip from '@/components/table-filter/SelectionChip.vue';
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
  'update:matches': [matches: MatchedKeywordWithBehaviour<any>];
}>();

defineSlots<{
  tooltip: () => any;
}>();

const { matchers, matches } = toRefs(props);

const input = ref();
const search = ref<string>('');
const selectedSuggestion = ref<number>(0);
const suggestedFilter = ref<Suggestion>({
  asset: false,
  index: 0,
  key: '',
  total: 0,
  value: '',
});
const shaking = ref<boolean>(false);

// Matcher utilities
const {
  matcherForKey,
  matcherForKeyValue,
  validKeys,
} = useMatcherUtils(matchers);

// Selection management
const {
  applyFilter,
  cancelEditSuggestion,
  clickItem,
  isSuggestionBeingEdited,
  restoreSelection,
  selection,
  suggestionBeingEdited,
  updateEditSuggestionSearch,
  updateMatches,
} = useFilterSelection(search, matcherForKey, matcherForKeyValue, emit);

// Filtered matchers based on selection
const { filteredMatchers } = useFilterMatchers(matchers, selection, search);

// Chip grouping composable
const {
  expandedGroupKey,
  getChipDisplayType,
  getGroupedItemsForKey,
  getGroupedOverflowCount,
  removeAllItemsForKey,
  removeGroupedItem,
  toggleGroupMenu,
} = useChipGrouping(selection, updateMatches);

const selectedMatcher = computed<SearchMatcher<any, any> | undefined>(() => {
  const searchKey = splitSearch(get(search));

  if (searchKey.exclude === undefined)
    return undefined;

  const key = get(validKeys).find(value => value === searchKey.key);
  return matcherForKey(key) ?? undefined;
});

function triggerShake(): void {
  set(shaking, true);
  setTimeout(() => {
    set(shaking, false);
  }, 500);
}

function setSearchToMatcherKey(matcher: SearchMatcher<any>): void {
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
  get(input)?.focus?.();
  nextTick(() => {
    set(search, filter);
  });
}

async function applySuggestion(): Promise<void> {
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
    set(selectedSuggestion, 0);
    set(search, '');
    return;
  }

  const searchVal = get(search);
  const { exclude, key, value: keyword } = splitSearch(searchVal);

  if (!key) {
    get(input).blur();
    set(selectedSuggestion, 0);
    set(search, '');
    return;
  }

  const matcher = matcherForKey(key);
  if (!matcher) {
    set(selectedSuggestion, 0);
    set(search, '');
    return;
  }

  let asset = false;
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

  // If there are no suggestions and the matcher has a validate function
  if (suggestedItems.length === 0 && 'validate' in matcher) {
    if (matcher.validate(keyword)) {
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
      set(selectedSuggestion, 0);
      set(search, '');
    }
    else {
      // Validation failed - keep search and shake
      triggerShake();
      const valueStart = key.length + (exclude ? 2 : 1);
      await nextTick(async () => {
        set(search, searchVal);
        await nextTick(() => {
          const inputEl = get(input)?.$el?.querySelector('input');
          inputEl?.setSelectionRange(valueStart, searchVal.length);
        });
      });
    }
    return;
  }

  cancelEditSuggestion();
  set(selectedSuggestion, 0);
  set(search, '');
}

function moveSuggestion(up: boolean): void {
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

  restoreSelection(get(matches));
});

watch(search, () => {
  set(selectedSuggestion, 0);
});

watch(matches, (matchesData) => {
  restoreSelection(matchesData);
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
            'animate-shake': shaking,
          }"
          hide-selection-wrapper
          :hide-search-input="!!suggestionBeingEdited"
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
            <SelectionChip
              v-model:expanded-group-key="expandedGroupKey"
              :item="item"
              :chip-attrs="chipAttrs"
              :display-type="getChipDisplayType(item)"
              :edit-mode="isSuggestionBeingEdited(item)"
              :overflow-count="getGroupedOverflowCount(item)"
              :grouped-items="getGroupedItemsForKey(item)"
              @click-item="clickItem($event)"
              @cancel-edit="cancelEditSuggestion($event)"
              @update:search="updateEditSuggestionSearch($event)"
              @toggle-group-menu="toggleGroupMenu($event)"
              @remove-all-items="removeAllItemsForKey($event)"
              @remove-grouped-item="removeGroupedItem($event)"
            />
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
