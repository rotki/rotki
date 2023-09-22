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
  <div class="flex flex-row">
    <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
      <template #activator="{ on }">
        <RuiButton
          icon
          size="sm"
          class="mr-2"
          variant="text"
          :disabled="selection.length === 0"
          v-on="on"
          @click="addToSavedFilter()"
        >
          <RuiIcon name="save-line" />
        </RuiButton>
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
    </RuiTooltip>

    <VMenu
      v-model="open"
      offset-y
      max-width="400"
      max-height="500"
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
          <template #activator="{ on: tooltipOn }">
            <RuiButton
              color="primary"
              size="sm"
              variant="text"
              icon
              v-on="{
                ...on,
                ...tooltipOn
              }"
            >
              <RuiIcon name="filter-line" />
            </RuiButton>
          </template>
          <span>{{ t('table_filter.saved_filters.actions.list') }}</span>
        </RuiTooltip>
      </template>
      <VList v-if="savedFilters.length > 0" class="py-4">
        <div v-for="(filters, index) in savedFilters" :key="index">
          <div v-if="index > 0" class="my-3 border-b" />
          <div class="flex px-4">
            <div class="flex grow flex-wrap pr-4">
              <VChip
                v-for="(filter, filterIndex) in filters"
                :key="filterIndex"
                label
                small
                class="ma-1"
              >
                <SuggestedItem chip :suggestion="filter" />
              </VChip>
            </div>
            <div class="flex">
              <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
                <template #activator="{ on }">
                  <RuiButton
                    color="success"
                    size="sm"
                    variant="text"
                    icon
                    v-on="on"
                    @click="applyFilter(filters)"
                  >
                    <RuiIcon name="filter-line" />
                  </RuiButton>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.apply') }}
                </span>
              </RuiTooltip>

              <RuiTooltip :popper="{ placement: 'top' }" open-delay="400">
                <template #activator="{ on }">
                  <RuiButton
                    icon
                    variant="text"
                    class="ml-2"
                    color="error"
                    size="sm"
                    v-on="on"
                    @click="deleteFilter(index)"
                  >
                    <RuiIcon name="delete-bin-line" />
                  </RuiButton>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.remove') }}
                </span>
              </RuiTooltip>
            </div>
          </div>
        </div>
      </VList>
      <div v-else class="pa-4">
        <i18n path="table_filter.saved_filters.empty">
          <template #button>
            <RuiButton icon variant="text" disabled size="sm">
              <RuiIcon name="save-line" />
            </RuiButton>
          </template>
        </i18n>
      </div>
    </VMenu>
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
