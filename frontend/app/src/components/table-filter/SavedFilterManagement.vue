<script lang="ts" setup>
import { type Ref } from 'vue';
import {
  type SavedFilterLocation,
  type SearchMatcher,
  type Suggestion
} from '@/types/filtering';

const props = defineProps<{
  matchers: SearchMatcher<any>[];
  selection: Suggestion[];
  location: SavedFilterLocation;
}>();

const emit = defineEmits<{
  (e: 'update:matches', matches: Suggestion[]): void;
}>();

const { selection, location, matchers } = toRefs(props);

const open: Ref<boolean> = ref(false);

const applyFilter = (filter: Suggestion[]) => {
  emit('update:matches', filter);
  set(open, false);
};

const added: Ref<boolean> = ref(false);
const { start, stop, isPending } = useTimeoutFn(
  () => {
    set(added, false);
  },
  4000,
  { immediate: false }
);

const { start: startAnimation } = useTimeoutFn(
  () => {
    set(added, true);
    start();
  },
  100,
  { immediate: false }
);

const isAsset = (searchKey: string): boolean => {
  const found = get(matchers).find(({ key }) => key === searchKey);
  return !!found && 'asset' in found;
};

const { savedFilters, addFilter, deleteFilter } = useSavedFilter(
  location,
  isAsset
);

const { setMessage } = useMessageStore();
const addToSavedFilter = async () => {
  const status = await addFilter(get(selection));
  if (status.success) {
    if (get(isPending)) {
      stop();
      set(added, false);
    }
    startAnimation();
  } else {
    setMessage({
      title: t('table_filter.saved_filters.saving.title').toString(),
      description: status.message,
      success: false
    });
  }
};

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <div class="d-flex">
    <v-tooltip top>
      <template #activator="{ on }">
        <v-btn
          icon
          fab
          x-small
          class="mr-2"
          :disabled="selection.length === 0"
          v-on="on"
          @click="addToSavedFilter()"
        >
          <v-icon>mdi-content-save-plus</v-icon>
        </v-btn>
      </template>
      <div class="text-center" :class="css['add-tooltip']">
        <div
          :class="{
            [css['add-tooltip__wrapper']]: true,
            [css['add-tooltip__wrapper--added']]: added
          }"
        >
          <div>{{ t('table_filter.saved_filters.actions.add') }}</div>
          <div class="green--text text--lighten-2">
            {{ t('table_filter.saved_filters.added') }}
          </div>
        </div>
      </div>
    </v-tooltip>

    <v-menu
      v-model="open"
      offset-y
      max-width="400"
      max-height="500"
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <v-tooltip top>
          <template #activator="{ on: tooltipOn }">
            <v-btn
              color="primary"
              x-small
              fab
              depressed
              v-on="{
                ...on,
                ...tooltipOn
              }"
            >
              <v-icon>mdi-filter-cog</v-icon>
            </v-btn>
          </template>
          <span>{{ t('table_filter.saved_filters.actions.list') }}</span>
        </v-tooltip>
      </template>
      <v-list v-if="savedFilters.length > 0" class="py-4">
        <div v-for="(filters, index) in savedFilters" :key="index">
          <v-divider v-if="index > 0" class="my-3" />
          <div class="d-flex px-4">
            <div class="d-flex flex-grow-1 flex-wrap pr-4">
              <v-chip
                v-for="(filter, filterIndex) in filters"
                :key="filterIndex"
                label
                small
                class="ma-1"
              >
                <suggested-item chip :suggestion="filter" />
              </v-chip>
            </div>
            <div class="d-flex">
              <v-tooltip top>
                <template #activator="{ on }">
                  <v-btn
                    color="green"
                    fab
                    x-small
                    depressed
                    v-on="on"
                    @click="applyFilter(filters)"
                  >
                    <v-icon color="white">mdi-filter-check</v-icon>
                  </v-btn>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.apply') }}
                </span>
              </v-tooltip>

              <v-tooltip top>
                <template #activator="{ on }">
                  <v-btn
                    icon
                    class="ml-2"
                    color="red"
                    fab
                    x-small
                    v-on="on"
                    @click="deleteFilter(index)"
                  >
                    <v-icon>mdi-delete-outline</v-icon>
                  </v-btn>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.remove') }}
                </span>
              </v-tooltip>
            </div>
          </div>
        </div>
      </v-list>
      <div v-else class="pa-4">
        <i18n path="table_filter.saved_filters.empty">
          <template #button>
            <v-btn icon fab disabled small>
              <v-icon>mdi-content-save-plus</v-icon>
            </v-btn>
          </template>
        </i18n>
      </div>
    </v-menu>
  </div>
</template>

<style module lang="scss">
.add-tooltip {
  height: 22px;
  overflow: hidden;

  &__wrapper {
    transition: 0.2s all;

    &--added {
      margin-top: -22px;
    }
  }
}
</style>
