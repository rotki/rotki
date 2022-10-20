<template>
  <div class="px-4 py-2">
    <div v-if="suggestion" class="pb-2">
      <div v-if="suggested.length > 0">
        <div
          v-for="(item, index) in suggested"
          :key="item.index"
          :tabindex="index"
        >
          <v-btn
            text
            color="primary"
            :class="{
              'fill-width': true,
              [css.selected]: index === selectedSuggestion
            }"
            class="text-none text-body-1"
            @click="applyFilter(item)"
          >
            <span class="text-start fill-width">
              <suggested-item :suggestion="item" />
            </span>
          </v-btn>
        </div>
      </div>
      <div v-else>
        <div class="text--secondary">
          {{ t('no_filter_available.no_suggestions', { search: keyword }) }}
        </div>
      </div>
      <div
        v-if="suggestion.hint"
        class="caption-text text--secondary text-wrap"
      >
        {{ suggestion.hint }}
      </div>
    </div>
    <div v-else-if="keyword" class="py-2">
      <span>{{ t('no_filter_available.unsupported_filter') }}</span>
      <span class="font-weight-medium ms-2">{{ keyword }}</span>
    </div>
    <div v-if="!suggestion">
      <div class="caption-text text--secondary">
        {{ t('no_filter_available.title') }}
      </div>
      <v-divider class="my-2" />
      <filter-entry
        v-for="matcher in available"
        :key="matcher.key"
        :matcher="matcher"
        @click="click($event)"
      />
      <v-divider class="mt-2" />
    </div>

    <div class="caption-text text--secondary text--lighten-2 mt-2">
      <span>{{ t('no_filter_available.hint.description') }}</span>
      <span class="font-weight-medium">
        {{ t('no_filter_available.hint.example') }}
      </span>
    </div>
    <div class="caption-text text--secondary text--lighten-2 mt-2">
      {{ t('no_filter_available.hint_filter') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { AssetInfo } from '@rotki/common/lib/data';
import { ComputedRef, PropType, Ref } from 'vue';
import FilterEntry from '@/components/history/filtering/FilterEntry.vue';
import SuggestedItem from '@/components/history/filtering/SuggestedItem.vue';
import { SearchMatcher, Suggestion } from '@/types/filtering';
import { compareSymbols } from '@/utils/assets';
import { logger } from '@/utils/logging';
import { splitSearch } from '@/utils/search';

const props = defineProps({
  matchers: {
    required: true,
    type: Array as PropType<SearchMatcher<any>[]>
  },
  used: {
    required: true,
    type: Array as PropType<string[]>
  },
  suggestion: {
    required: false,
    type: Object as PropType<SearchMatcher<any> | null>,
    default: null
  },
  keyword: {
    required: false,
    type: String,
    default: null
  },
  selectedSuggestion: {
    required: true,
    type: Number
  }
});

const emit = defineEmits<{
  (e: 'click', item: string): void;
  (e: 'suggest', item: Suggestion): void;
  (e: 'apply:filter', item: Suggestion): void;
}>();

const { keyword, suggestion, selectedSuggestion } = toRefs(props);

const css = useCssModule();

const lastSuggestion: Ref<Suggestion | null> = ref(null);
const suggested: Ref<Suggestion[]> = ref([]);

const available: ComputedRef<SearchMatcher<any>[]> = computed(
  ({ matchers, used }: { matchers: SearchMatcher<any>[]; used: string[] }) =>
    matchers.filter(({ key, multiple }) => !used.includes(key) || multiple)
);

const updateSuggestion = (value: Suggestion[], index: number) => {
  set(lastSuggestion, value[index]);
  emit('suggest', {
    key: value[index].key,
    value: value[index].value,
    index: index,
    total: value.length
  });
};

const click = (key: string) => {
  if (key.trim().length) {
    emit('click', key);
  }
};

const applyFilter = (item: Suggestion) => {
  let value = typeof item.value === 'string' ? item.value : item.value.symbol;
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

watch([keyword, suggestion], async ([keyword, suggestion]) => {
  if (!keyword || !suggestion) {
    return [];
  }

  const search = splitSearch(keyword);
  const suggestedFilter = suggestion.key;

  const searchString = search[1] ?? '';
  let suggestedItems: { key: string; value: string | AssetInfo }[] = [];
  if ('string' in suggestion) {
    suggestedItems = suggestion.suggestions().map(item => ({
      key: suggestedFilter,
      value: item
    }));
  } else if ('asset' in suggestion) {
    if (searchString) {
      suggestedItems = (await suggestion.suggestions(searchString)).map(
        asset => {
          return {
            key: suggestedFilter,
            value: asset
          };
        }
      );
    }
  } else {
    logger.debug('Matcher is missing asset=true or string=true', suggestion);
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
        total: suggestedItems.length,
        index,
        key: a.key,
        value: a.value
      }))
  );
});

const { t } = useI18n();
</script>

<style module lang="scss">
.selected {
  background-color: var(--v-primary-lighten4);
}
</style>
