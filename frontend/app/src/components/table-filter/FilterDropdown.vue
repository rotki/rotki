<script setup lang="ts">
import { type AssetInfo } from '@rotki/common/lib/data';
import { type Ref } from 'vue';
import { type SearchMatcher, type Suggestion } from '@/types/filtering';

const props = withDefaults(
  defineProps<{
    matchers: SearchMatcher<any>[];
    selectedMatcher?: SearchMatcher<any> | null;
    keyword?: string;
    selectedSuggestion: number;
  }>(),
  {
    selectedMatcher: null,
    keyword: ''
  }
);

const emit = defineEmits<{
  (e: 'click', item: SearchMatcher<any>): void;
  (e: 'suggest', item: Suggestion): void;
  (e: 'apply:filter', item: Suggestion): void;
}>();

const { keyword, selectedMatcher, selectedSuggestion } = toRefs(props);

const keywordSplited = computed(() => splitSearch(get(keyword)));

const css = useCssModule();

const lastSuggestion: Ref<Suggestion | null> = ref(null);
const suggested: Ref<Suggestion[]> = ref([]);

const updateSuggestion = (value: Suggestion[], index: number) => {
  set(lastSuggestion, value[index]);
  emit('suggest', {
    ...value[index],
    index,
    total: value.length
  });
};

const click = (matcher: SearchMatcher<any>) => {
  emit('click', matcher);
};

const applyFilter = (item: Suggestion) => {
  const value = typeof item.value === 'string' ? item.value : item.value.symbol;
  if (value) {
    emit('apply:filter', item);
  }
};

watch(selectedSuggestion, index => {
  updateSuggestion(get(suggested), index);
});

watch(suggested, value => {
  if (value.length > 0) {
    if (get(lastSuggestion) !== value[0]) {
      updateSuggestion(value, 0);
    }
  } else {
    set(lastSuggestion, null);
    emit('suggest', { key: '', index: 0, total: 0 } as Suggestion);
  }
});

watch([keyword, selectedMatcher], async ([keyword, selectedMatcher]) => {
  if (!keyword || !selectedMatcher) {
    return [];
  }

  const search = splitSearch(keyword);
  const exclude =
    'string' in selectedMatcher &&
    !!selectedMatcher.allowExclusion &&
    !!search.exclude;

  const suggestedFilter = selectedMatcher.key;

  const searchString = search.value ?? '';
  let suggestedItems: {
    key: string;
    value: string | AssetInfo;
    exclude: boolean;
  }[] = [];

  if ('string' in selectedMatcher) {
    suggestedItems = selectedMatcher.suggestions().map(item => ({
      key: suggestedFilter,
      value: item,
      exclude
    }));
  } else if ('asset' in selectedMatcher) {
    if (searchString) {
      suggestedItems = (await selectedMatcher.suggestions(searchString)).map(
        asset => ({
          key: suggestedFilter,
          value: asset,
          exclude
        })
      );
    }
  } else {
    logger.debug(
      'Matcher is missing asset=true or string=true',
      selectedMatcher
    );
  }

  set(
    suggested,
    suggestedItems
      .sort((a, b) => {
        const aText =
          typeof a.value === 'string'
            ? a.value
            : `${a.value.symbol} ${a.value.evmChain}`;
        const bText =
          typeof b.value === 'string'
            ? b.value
            : `${b.value.symbol} ${b.value.evmChain}`;
        return compareSymbols(aText, bText, searchString);
      })
      .slice(0, 5)
      .map((a, index) => ({
        index,
        key: a.key,
        value: a.value,
        asset: typeof a.value !== 'string',
        total: suggestedItems.length,
        exclude
      }))
  );
});

const { t } = useI18n();

watch(selectedSuggestion, () => {
  if (get(selectedMatcher)) {
    return;
  }
  nextTick(() => {
    document
      .getElementsByClassName('highlightedMatcher')[0]
      ?.scrollIntoView?.({ block: 'nearest' });
  });
});

const highlightedTextClasses = 'text-subtitle-2 text--secondary';
</script>

<template>
  <div class="px-4 py-1">
    <div v-if="selectedMatcher">
      <div v-if="suggested.length > 0" class="mb-2" :class="css.suggestions">
        <div
          v-for="(item, index) in suggested"
          :key="item.index"
          :tabindex="index"
        >
          <VBtn
            text
            color="primary"
            :class="{
              [css.selected]: index === selectedSuggestion
            }"
            class="text-none text-body-1 px-3 fill-width"
            @click="applyFilter(item)"
          >
            <span class="text-start fill-width">
              <SuggestedItem :suggestion="item" />
            </span>
          </VBtn>
        </div>
      </div>
      <div v-else class="pb-0">
        <div class="text--secondary">
          <I18n path="table_filter.no_suggestions">
            <template #search>
              <span class="font-weight-medium">
                {{ keywordSplited.key }}
              </span>
            </template>
          </I18n>
        </div>
      </div>

      <div
        v-if="'string' in selectedMatcher && selectedMatcher.allowExclusion"
        :class="highlightedTextClasses"
        class="font-weight-regular pt-2"
      >
        {{ t('table_filter.exclusion.description') }}
        <span class="font-weight-medium">
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
    <div v-else-if="keyword && matchers.length === 0" class="pb-2">
      <span>{{ t('table_filter.unsupported_filter') }}</span>
      <span class="font-weight-medium ms-2">{{ keyword }}</span>
    </div>
    <div v-if="!selectedMatcher && matchers.length > 0">
      <div
        :class="highlightedTextClasses"
        class="text-uppercase font-weight-bold"
      >
        {{ t('table_filter.title') }}
      </div>
      <VDivider class="my-2" />
      <div :class="css.suggestions">
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
    <div :class="highlightedTextClasses" class="font-weight-regular mt-2">
      <VDivider class="my-2" />
      <span>{{ t('table_filter.hint.description') }}</span>
      <span class="font-weight-medium">
        {{ t('table_filter.hint.example') }}
      </span>
      <div>
        {{ t('table_filter.hint_filter') }}
      </div>
    </div>
  </div>
</template>

<style module lang="scss">
.selected {
  background-color: var(--v-primary-lighten4);
}

.suggestions {
  max-height: 180px;
  overflow-y: scroll;
}
</style>
