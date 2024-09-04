<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { get, set } from '@vueuse/core';
import type { BaseSuggestion, SearchMatcher, Suggestion } from '@/types/filtering';

const props = defineProps<{
  matchers: SearchMatcher<any>[];
  selectedMatcher?: SearchMatcher<any>;
  keyword: string;
  selectedSuggestion: number;
}>();

const emit = defineEmits<{
  (e: 'click', item: SearchMatcher<any>): void;
  (e: 'suggest', item: Suggestion): void;
  (e: 'apply-filter', item: Suggestion): void;
  (e: 'update:keyword', value: string): void;
}>();

const { keyword, selectedMatcher, selectedSuggestion } = toRefs(props);

const keywordSplited = computed(() => splitSearch(get(keyword)));

const lastSuggestion = ref<Suggestion | null>(null);
const suggested = ref<Suggestion[]>([]);
const noSuggestionsForValue = ref(false);
const isExactMatch = ref(false);

function updateSuggestion(value: Suggestion[], index: number) {
  set(lastSuggestion, value[index]);
  emit('suggest', {
    ...value[index],
    index,
    total: value.length,
  });
}

function click(matcher: SearchMatcher<any>) {
  emit('click', matcher);
}

function applyFilter(item: Suggestion) {
  const value = typeof item.value === 'string' ? item.value : item.value.symbol;
  if (value) {
    emit('apply-filter', item);
    emit('update:keyword', `${item.key}=${value}`);
  }
}

watch(selectedSuggestion, (index) => {
  updateSuggestion(get(suggested), index);
});

watch(suggested, (value) => {
  if (value.length > 0) {
    if (get(lastSuggestion) !== value[0])
      updateSuggestion(value, 0);
  }
  else {
    set(lastSuggestion, null);
    emit('suggest', { key: '', index: 0, total: 0 } as Suggestion);
  }
});

watch(
  [keyword, selectedMatcher],
  async ([keyword, selectedMatcher]) => {
    if (!keyword)
      return;

    const search = splitSearch(keyword);
    const searchString = search.value ?? '';
    let suggestedItems: BaseSuggestion[] = [];

    const exactMatcher = props.matchers.find(m => m.key.toLowerCase() === keyword.toLowerCase());
    if (exactMatcher) {
      suggestedItems = [{
        key: exactMatcher.key,
        value: exactMatcher.description,
      }];
      set(noSuggestionsForValue, false);
      set(isExactMatch, true);
    }
    else if (selectedMatcher) {
      if ('string' in selectedMatcher) {
        const exclude = !!selectedMatcher.allowExclusion && !!search.exclude;
        suggestedItems = selectedMatcher.suggestions().map(item => ({
          key: selectedMatcher.key,
          value: item,
          exclude,
        }));
      }
      else if ('asset' in selectedMatcher) {
        if (searchString) {
          suggestedItems = (await selectedMatcher.suggestions(searchString)).map(asset => ({
            key: selectedMatcher.key,
            value: asset,
            exclude: false,
          }));
        }
      }
      else if ('boolean' in selectedMatcher) {
        suggestedItems = [{
          key: selectedMatcher.key,
          value: true,
          exclude: false,
        }];
      }
      set(noSuggestionsForValue, suggestedItems.length === 0 && !!searchString);
      set(isExactMatch, false);
    }
    else {
      set(noSuggestionsForValue, false);
      set(isExactMatch, false);
    }

    const getItemText = (item: BaseSuggestion) =>
      typeof item.value === 'string' ? item.value : `${item.value.symbol} ${item.value.evmChain ?? ''}`;

    set(
      suggested,
      suggestedItems
        .sort((a, b) => compareTextByKeyword(getItemText(a), getItemText(b), searchString))
        .map((item, index) => ({
          index,
          key: item.key,
          value: item.value,
          asset: typeof item.value !== 'string',
          total: suggestedItems.length,
          exclude: item.exclude,
        })),
    );
  },
  { immediate: true },
);

const { t } = useI18n();

watch(selectedSuggestion, async () => {
  if (get(selectedMatcher))
    return;

  await nextTick(() => {
    document.getElementsByClassName('highlightedMatcher')[0]?.scrollIntoView?.({ block: 'nearest' });
  });
});

const highlightedTextClasses = 'text-subtitle-2 text-rui-text-secondary';

function handleEnter() {
  const currentKeyword = get(keyword);
  const matcher = props.matchers.find(m => m.key.toLowerCase() === currentKeyword.toLowerCase());

  if (matcher) {
    const exactSuggestion: Suggestion = {
      key: matcher.key,
      value: matcher.description,
      index: 0,
      total: 1,
      asset: false,
      exclude: false,
    };

    emit('update:keyword', `${matcher.key}=`);
    emit('apply-filter', exactSuggestion);
  }
  else if (get(suggested).length > 0) {
    applyFilter(get(suggested)[get(selectedSuggestion)]);
  }
}

function getDisplayValue(suggestion: Suggestion) {
  if (typeof suggestion.value === 'string')
    return suggestion.value;

  return suggestion.value.symbol;
}
</script>

<template>
  <div class="px-4 py-1">
    <div v-if="selectedMatcher || suggested.length > 0">
      <div
        :class="highlightedTextClasses"
        class="uppercase font-bold mb-2"
      >
        {{ t('table_filter.title') }}
      </div>
      <RuiDivider class="my-2" />
      <div
        v-if="suggested.length > 0"
        class="mb-2"
        :class="$style.suggestions"
        data-cy="suggestions"
      >
        <RuiButton
          v-for="(item, index) in suggested"
          :key="item.index"
          :tabindex="index"
          variant="text"
          class="text-body-1 tracking-wide w-full justify-start text-left text-rui-text-secondary p-0"
          :class="{
            ['!bg-rui-primary-lighter/20']: index === selectedSuggestion,
          }"
          @click="applyFilter(item)"
          @keydown.enter="handleEnter()"
        >
          <div class="flex items-center w-full px-3 py-2">
            <span class="text-rui-primary font-bold min-w-[4rem] text-left">{{ item.key }}:</span>
            <span class="font-normal ml-2">{{ getDisplayValue(item) }}</span>
          </div>
        </RuiButton>
      </div>
      <div
        v-else-if="noSuggestionsForValue"
        class="pb-0 text-rui-text-secondary"
        data-cy="no-suggestions"
      >
        <i18n-t
          v-if="selectedMatcher && !('asset' in selectedMatcher)"
          keypath="table_filter.no_suggestions"
          tag="span"
        >
          <template #search>
            <span class="font-medium text-rui-primary">
              {{ keywordSplited.value }}
            </span>
          </template>
        </i18n-t>
        <template v-else-if="selectedMatcher && 'asset' in selectedMatcher">
          {{ t('table_filter.asset_suggestion') }}
        </template>
      </div>

      <div
        v-if="selectedMatcher && 'string' in selectedMatcher && selectedMatcher.allowExclusion"
        :class="highlightedTextClasses"
        class="font-light pt-2"
      >
        {{ t('table_filter.exclusion.description') }}
        <span class="font-medium">
          {{ t('table_filter.exclusion.example') }}
        </span>
      </div>

      <div
        v-if="selectedMatcher && selectedMatcher.hint"
        :class="highlightedTextClasses"
        class="text-wrap"
      >
        {{ selectedMatcher.hint }}
      </div>
    </div>
    <div
      v-else-if="keyword && matchers.length === 0"
      class="pb-0"
    >
      <span>{{ t('table_filter.unsupported_filter') }}</span>
      <span class="font-medium ms-2">{{ keyword }}</span>
    </div>
    <div v-else-if="!selectedMatcher && matchers.length > 0">
      <div
        :class="highlightedTextClasses"
        class="uppercase font-bold"
      >
        {{ t('table_filter.title') }}
      </div>
      <RuiDivider class="my-2" />
      <div
        :class="$style.suggestions"
        data-cy="suggestions"
      >
        <FilterEntry
          v-for="(matcher, index) in matchers"
          :key="matcher.key"
          :active="index === selectedSuggestion"
          :matcher="matcher"
          :class="{ highlightedMatcher: index === selectedSuggestion }"
          @click="click(matcher)"
          @keydown.enter="handleEnter()"
        >
          <span class="font-bold text-rui-primary-main">{{ matcher.key }}:</span> {{ t(`table_filter.filter.${matcher.key}`) }}
        </FilterEntry>
      </div>
    </div>
    <div
      :class="highlightedTextClasses"
      class="font-light mt-2"
    >
      <RuiDivider class="my-2" />
      <span>{{ t('table_filter.hint.description') }}</span>
      <span class="font-medium">
        {{ t('table_filter.hint.example') }}
      </span>
      <div>
        {{ t('table_filter.hint_filter') }}
      </div>
      <div class="mt-1 text-rui-text-secondary-dark italic">
        {{ t('table_filter.hint.edit_note') }}
      </div>
    </div>
  </div>
</template>

<style lang="scss" module>
.suggestions {
  @apply max-h-[12rem] overflow-y-auto;
}
</style>
