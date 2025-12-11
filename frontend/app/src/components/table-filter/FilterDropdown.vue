<script setup lang="ts">
import type { BaseSuggestion, MatchedKeywordWithBehaviour, SearchMatcher, Suggestion } from '@/types/filtering';
import FilterEntry from '@/components/table-filter/FilterEntry.vue';
import SuggestedItem from '@/components/table-filter/SuggestedItem.vue';
import { compareTextByKeyword } from '@/utils/assets';
import { logger } from '@/utils/logging';
import { splitSearch } from '@/utils/search';

const props = defineProps<{
  matches: MatchedKeywordWithBehaviour<any>;
  matchers: SearchMatcher<any>[];
  selectedMatcher?: SearchMatcher<any>;
  keyword: string;
  selectedSuggestion: number;
}>();

const emit = defineEmits<{
  (e: 'click', item: SearchMatcher<any>): void;
  (e: 'suggest', item: Suggestion): void;
  (e: 'apply-filter', item: Suggestion): void;
}>();

const { keyword, selectedMatcher, selectedSuggestion } = toRefs(props);

const keywordSplit = computed(() => splitSearch(get(keyword)));

const lastSuggestion = ref<Suggestion | null>(null);
const suggested = ref<Suggestion[]>([]);

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
  if (value)
    emit('apply-filter', item);
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
    emit('suggest', { index: 0, key: '', total: 0 } as Suggestion);
  }
});

watch([keyword, selectedMatcher], async ([keyword, selectedMatcher]) => {
  if (!keyword || !selectedMatcher)
    return [];

  const search = splitSearch(keyword);
  const suggestedFilter = selectedMatcher.key;

  const searchString = search.value ?? '';

  let suggestedItems: BaseSuggestion[] = [];

  let exclude = false;
  let asset = false;
  if ('string' in selectedMatcher) {
    exclude = !!selectedMatcher.allowExclusion && !!search.exclude;
    suggestedItems = selectedMatcher.suggestions().map(item => ({
      exclude,
      key: suggestedFilter,
      value: item,
    }));
  }
  else if ('asset' in selectedMatcher) {
    if (searchString) {
      asset = true;
      try {
        const suggestions = await selectedMatcher.suggestions(searchString);
        if (suggestions) {
          suggestedItems = suggestions.map(asset => ({
            exclude,
            key: suggestedFilter,
            value: asset,
          }));
        }
      }
      catch (error) {
        logger.error(error);
        suggestedItems = [];
      }
    }
  }
  else if ('boolean' in selectedMatcher) {
    suggestedItems = [
      {
        exclude: false,
        key: suggestedFilter,
        value: true,
      },
    ];
  }
  else {
    logger.debug('Matcher doesn\'t have asset=true, string=true, or boolean=true.', selectedMatcher);
  }

  const getItemText = (item: BaseSuggestion) =>
    typeof item.value === 'string' ? item.value : `${item.value.symbol} ${item.value.evmChain}`;

  const limit = selectedMatcher.suggestionsToShow || (asset ? 10 : 5);

  set(suggested, suggestedItems
    .sort((a, b) => compareTextByKeyword(getItemText(a), getItemText(b), searchString))
    .slice(0, limit)
    .map((a, index) => ({
      asset: typeof a.value !== 'string',
      exclude,
      index,
      key: a.key,
      total: suggestedItems.length,
      value: a.value,
    })));
}, { immediate: true });

const { t } = useI18n({ useScope: 'global' });

watch(selectedSuggestion, async () => {
  await nextTick(() => {
    document.getElementsByClassName('highlightedMatcher')[0]?.scrollIntoView?.({ block: 'nearest' });
  });
});

const highlightedTextClasses = 'text-subtitle-2 text-rui-text-secondary';
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
