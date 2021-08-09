<template>
  <div class="px-4 py-2">
    <div v-if="suggestion" class="pb-2">
      <div v-for="(text, index) in suggest" :key="text" :tabindex="index">
        <v-btn
          text
          color="primary"
          :class="{
            [$style.fullwidth]: true,
            [$style.selected]: index === selectedSuggestion
          }"
          class="text-none text-body-1"
          @click="applyFilter(text)"
        >
          <span class="text-start" :class="$style.fullwidth">
            <span class="font-weight-medium">
              {{ text }}
            </span>
          </span>
        </v-btn>
      </div>
      <div
        v-if="suggestion.hint"
        class="caption-text text--secondary text-wrap"
      >
        {{ suggestion.hint }}
      </div>
    </div>
    <div v-else-if="keyword" class="py-2">
      <span>{{ $t('no_filter_available.unsupported_filter') }}</span>
      <span class="font-weight-medium ms-2">{{ keyword }}</span>
    </div>
    <div v-if="!suggestion">
      <div class="caption-text text--secondary">
        {{ $t('no_filter_available.title') }}
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
      <span>{{ $t('no_filter_available.hint.description') }}</span>
      <span class="font-weight-medium">
        {{ $t('no_filter_available.hint.example') }}
      </span>
    </div>
    <div class="caption-text text--secondary text--lighten-2 ms-2">
      {{ $t('no_filter_available.hint_filter') }}
    </div>
  </div>
</template>

<script lang="ts">
import { Nullable } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  ref,
  toRefs,
  watch
} from '@vue/composition-api';
import FilterEntry from '@/components/history/filtering/FilterEntry.vue';
import {
  SearchMatcher,
  Suggestion
} from '@/components/history/filtering/types';
import { splitSearch } from '@/components/history/filtering/utils';
import { compareSymbols } from '@/utils/assets';

export default defineComponent({
  name: 'NoFilterAvailable',
  components: { FilterEntry },
  props: {
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
  },
  emits: {
    click: (key: string) => {
      return key.trim().length > 0;
    },
    'apply:filter': (filter: string) => {
      return filter.length > 0;
    }
  },
  setup(props, { emit }) {
    const available = computed<SearchMatcher<any>[]>(
      ({
        matchers,
        used
      }: {
        matchers: SearchMatcher<any>[];
        used: string[];
      }) => matchers.filter(({ key }) => !used.includes(key))
    );

    const suggest = computed<string[]>(
      ({
        keyword,
        suggestion
      }: {
        keyword: Nullable<string>;
        suggestion: Nullable<SearchMatcher<any>>;
      }) => {
        if (!keyword || !suggestion) {
          return [];
        }

        const search = splitSearch(keyword);
        const suggestedFilter = suggestion.key;

        const searchString = search[1] ?? '';
        const suggestions: string[] = suggestion
          .suggestions()
          .sort((a, b) => compareSymbols(a, b, searchString))
          .map(sug => `${suggestedFilter}: ${sug}`)
          .slice(0, 5);
        if (suggestions.includes(keyword)) {
          return [keyword];
        }

        return suggestions;
      }
    );

    const lastSuggestion = ref('');
    const { selectedSuggestion } = toRefs(props);

    function updateSuggestion(value: string[], index: number) {
      lastSuggestion.value = value[index];
      emit('suggest', {
        suggestion: value[index],
        index: index,
        total: value.length
      } as Suggestion);
    }

    watch(selectedSuggestion, index => {
      updateSuggestion(suggest.value, index);
    });
    watch(suggest, value => {
      if (value.length > 0) {
        if (lastSuggestion.value !== value[0]) {
          updateSuggestion(value, 0);
        }
      } else {
        lastSuggestion.value = '';
        emit('suggest', { suggestion: '', index: 0, total: 0 } as Suggestion);
      }
    });

    const click = (key: string) => {
      emit('click', key);
    };
    const applyFilter = (filter: string) => {
      emit('apply:filter', filter);
    };
    return {
      click,
      applyFilter,
      suggest,
      available
    };
  }
});
</script>

<style module>
.fullwidth {
  width: 100%;
}

.selected {
  background-color: var(--v-primary-lighten4);
}
</style>
