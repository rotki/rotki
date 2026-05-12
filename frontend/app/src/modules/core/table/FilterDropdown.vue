<script setup lang="ts">
import { getTextToken } from '@rotki/common';
import { type SplitResult, splitSearch } from '@/modules/core/common/data/search';
import { compareTextByKeyword } from '@/modules/core/common/display/assets';
import { logger } from '@/modules/core/common/logging/logging';
import FilterEntry from '@/modules/core/table/FilterEntry.vue';
import {
  type BaseSuggestion,
  createEmptySuggestion,
  type MatchedKeywordWithBehaviour,
  type SearchMatcher,
  type Suggestion,
} from '@/modules/core/table/filtering';
import SuggestedItem from '@/modules/core/table/SuggestedItem.vue';

interface ResolvedSuggestions {
  items: BaseSuggestion[];
  exclude: boolean;
  asset: boolean;
}

const { keyword, matchers, selectedMatcher, selectedSuggestion, defaultMatcherKey } = defineProps<{
  matches: MatchedKeywordWithBehaviour<any>;
  matchers: SearchMatcher<any>[];
  selectedMatcher?: SearchMatcher<any>;
  keyword: string;
  selectedSuggestion: number;
  defaultMatcherKey?: string;
}>();

const emit = defineEmits<{
  'click': [item: SearchMatcher<any>];
  'suggest': [item: Suggestion];
  'apply-filter': [item: Suggestion];
}>();

const { t } = useI18n({ useScope: 'global' });

const highlightedTextClasses = 'text-subtitle-2 text-rui-text-secondary';

const lastSuggestion = ref<Suggestion | null>(null);
const suggested = ref<Suggestion[]>([]);

const keywordSplit = computed<SplitResult>(() => splitSearch(keyword));
const showDefaultMatcherHint = computed<boolean>(() =>
  !!defaultMatcherKey && matchers.length === 0 && !!keyword && get(keywordSplit).exclude === undefined,
);

function updateSuggestion(value: Suggestion[], index: number): void {
  set(lastSuggestion, value[index]);
  emit('suggest', {
    ...value[index],
    index,
    total: value.length,
  });
}

function click(matcher: SearchMatcher<any>): void {
  emit('click', matcher);
}

function applyFilter(item: Suggestion): void {
  const value = typeof item.value === 'string' ? item.value : item.value.symbol;
  if (value)
    emit('apply-filter', item);
}

function buildStringSuggestions(matcher: SearchMatcher<any>, searchString: string, allowExclude: boolean): ResolvedSuggestions {
  if (!('string' in matcher))
    return { asset: false, exclude: false, items: [] };

  const exclude = !!matcher.allowExclusion && allowExclude;
  let suggestions = matcher.suggestions();

  // When strictMatching is enabled, filter suggestions to only include those containing the keyword.
  if (matcher.strictMatching && searchString) {
    const tokenizedSearch = getTextToken(searchString);
    suggestions = suggestions.filter(item => getTextToken(item).includes(tokenizedSearch));
  }

  return {
    asset: false,
    exclude,
    items: suggestions.map(item => ({ exclude, key: matcher.key, value: item })),
  };
}

async function buildAssetSuggestions(matcher: SearchMatcher<any>, searchString: string): Promise<ResolvedSuggestions> {
  if (!('asset' in matcher) || !searchString)
    return { asset: false, exclude: false, items: [] };

  try {
    const suggestions = await matcher.suggestions(searchString);
    return {
      asset: true,
      exclude: false,
      items: (suggestions ?? []).map(value => ({ exclude: false, key: matcher.key, value })),
    };
  }
  catch (error) {
    logger.error(error);
    return { asset: true, exclude: false, items: [] };
  }
}

function buildBooleanSuggestions(matcher: SearchMatcher<any>): ResolvedSuggestions {
  return {
    asset: false,
    exclude: false,
    items: [{ exclude: false, key: matcher.key, value: true }],
  };
}

async function resolveSuggestions(matcher: SearchMatcher<any>, search: SplitResult): Promise<ResolvedSuggestions> {
  const searchString = search.value ?? '';

  if ('string' in matcher)
    return buildStringSuggestions(matcher, searchString, !!search.exclude);

  if ('asset' in matcher)
    return buildAssetSuggestions(matcher, searchString);

  if ('boolean' in matcher)
    return buildBooleanSuggestions(matcher);

  logger.debug('Matcher doesn\'t have asset=true, string=true, or boolean=true.', matcher);
  return { asset: false, exclude: false, items: [] };
}

function getSuggestionText(item: BaseSuggestion): string {
  return typeof item.value === 'string' ? item.value : `${item.value.symbol} ${item.value.evmChain}`;
}

watch(() => selectedSuggestion, (index) => {
  updateSuggestion(get(suggested), index);
});

watch(suggested, (value) => {
  if (value.length > 0) {
    if (get(lastSuggestion) !== value[0])
      updateSuggestion(value, 0);
  }
  else {
    set(lastSuggestion, null);
    emit('suggest', createEmptySuggestion());
  }
});

watch([() => keyword, () => selectedMatcher], async ([keyword, selectedMatcher]) => {
  if (!keyword || !selectedMatcher)
    return;

  const search = splitSearch(keyword);
  const searchString = search.value ?? '';
  const { asset, exclude, items } = await resolveSuggestions(selectedMatcher, search);

  const limit = selectedMatcher.suggestionsToShow ?? (asset ? 10 : 5);
  const sorted = items.sort((a, b) => compareTextByKeyword(getSuggestionText(a), getSuggestionText(b), searchString));
  const limited = limit < 0 ? sorted : sorted.slice(0, limit);

  set(suggested, limited.map((a, index) => ({
    asset: typeof a.value !== 'string',
    exclude,
    index,
    key: a.key,
    total: items.length,
    value: a.value,
  })));
}, { immediate: true });

watch(() => selectedSuggestion, async () => {
  await nextTick(() => {
    document.getElementsByClassName('highlightedMatcher')[0]?.scrollIntoView?.({ block: 'nearest' });
  });
});
</script>

<template>
  <div class="p-3">
    <div
      v-if="selectedMatcher"
      class="flex flex-col gap-1"
    >
      <div
        v-if="suggested.length > 0"
        class="max-h-[12rem] overflow-x-hidden overflow-y-auto"
        data-cy="suggestions"
      >
        <RuiButton
          v-for="(item, index) in suggested"
          :key="item.index"
          :tabindex="index"
          variant="text"
          class="text-body-1 tracking-wide w-full justify-start text-left text-rui-text-secondary"
          :class="{
            ['!bg-rui-primary-lighter/20 highlightedMatcher']: index === selectedSuggestion,
          }"
          @click="applyFilter(item)"
        >
          <SuggestedItem :suggestion="item" />
        </RuiButton>
      </div>
      <div
        v-else
        class="text-rui-text-secondary"
      >
        <i18n-t
          v-if="!('asset' in selectedMatcher)"
          scope="global"
          keypath="table_filter.start_typing"
          tag="div"
        >
          <template #search>
            <span class="font-medium text-rui-primary">
              {{ keywordSplit.key }}
            </span>
          </template>
        </i18n-t>
        <template v-else>
          {{ t('table_filter.asset_suggestion') }}
        </template>
      </div>

      <div
        v-if="'string' in selectedMatcher && selectedMatcher.allowExclusion"
        :class="highlightedTextClasses"
        class="font-light mt-2"
      >
        {{ t('table_filter.exclusion.description') }}
        <span class="font-medium">
          {{ t('table_filter.exclusion.example') }}
        </span>
      </div>

      <div
        v-if="selectedMatcher.hint"
        :class="highlightedTextClasses"
        class="text-wrap"
      >
        {{ selectedMatcher.hint }}
      </div>
    </div>
    <div
      v-else-if="showDefaultMatcherHint"
    >
      <span>{{ t('table_filter.press_enter_to_apply') }}</span>
      <span class="font-medium ms-2">{{ defaultMatcherKey }}={{ keyword }}</span>
    </div>
    <div
      v-else-if="keyword && matchers.length === 0"
    >
      <span>{{ t('table_filter.unsupported_filter') }}</span>
      <span class="font-medium ms-2">{{ keyword }}</span>
    </div>
    <div v-if="!selectedMatcher && matchers.length > 0">
      <div
        :class="highlightedTextClasses"
        class="uppercase font-bold"
      >
        {{ t('table_filter.title') }}
      </div>
      <RuiDivider class="my-2" />
      <div
        class="max-h-[12rem] overflow-x-hidden overflow-y-auto"
        data-cy="suggestions"
      >
        <FilterEntry
          v-for="(matcher, index) in matchers"
          :key="matcher.key"
          :active="index === selectedSuggestion"
          :matcher="matcher"
          :class="{ highlightedMatcher: index === selectedSuggestion }"
          @click="click($event)"
        />
      </div>
    </div>
    <RuiDivider class="my-2" />
    <div
      :class="highlightedTextClasses"
      class="mt-3 flex flex-col gap-2"
    >
      <div class="flex items-center gap-2">
        <RuiIcon
          name="lu-keyboard"
          size="16"
          class="min-w-4"
        />
        <span>
          <span>{{ t('table_filter.hint.description') }}</span>
          <span class="font-medium">
            {{ t('table_filter.hint.example') }}
          </span>
        </span>
      </div>
      <div
        v-if="Object.values(matches).length > 0"
        class="flex items-center gap-2"
      >
        <RuiIcon
          name="lu-info"
          size="16"
          class="min-w-4"
        />
        {{ t('table_filter.hint.edit_note') }}
      </div>
    </div>
  </div>
</template>
