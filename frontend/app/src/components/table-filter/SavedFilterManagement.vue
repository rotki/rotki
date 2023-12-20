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
  disabled: boolean;
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
  <div class="flex items-center">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
      :disabled="disabled"
    >
      <template #activator>
        <RuiButton
          color="secondary"
          variant="text"
          icon
          :disabled="disabled || selection.length === 0"
          @click="addToSavedFilter()"
        >
          <RuiIcon size="20" name="play-list-add-line" />
        </RuiButton>
      </template>
      <div class="text-center" :class="css['add-tooltip']">
        <div class="h-4 transition-all" :class="{ '-mt-4': added }">
          <div>
            {{ t('table_filter.saved_filters.actions.add') }}
          </div>
          <div class="text-rui-success-lighter">
            {{ t('table_filter.saved_filters.added') }}
          </div>
        </div>
      </div>
    </RuiTooltip>

    <VMenu
      v-model="open"
      offset-y
      left
      max-width="400"
      max-height="500"
      :close-on-content-click="false"
    >
      <template #activator="{ on }">
        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
          :disabled="disabled"
        >
          <template #activator>
            <RuiButton
              :disabled="disabled"
              color="primary"
              variant="text"
              icon
              v-on="on"
            >
              <RuiIcon size="20" name="filter-line" />
            </RuiButton>
          </template>
          <span>{{ t('table_filter.saved_filters.actions.list') }}</span>
        </RuiTooltip>
      </template>
      <div v-if="savedFilters.length > 0" class="py-4">
        <div v-for="(filters, index) in savedFilters" :key="index">
          <RuiDivider v-if="index > 0" class="my-3" />
          <div class="flex px-4">
            <div class="flex flex-wrap pr-4 gap-1">
              <RuiChip
                v-for="(filter, filterIndex) in filters"
                :key="filterIndex"
                tile
                size="sm"
                class="font-medium !py-0"
              >
                <SuggestedItem chip :suggestion="filter" />
              </RuiChip>
            </div>
            <div class="flex items-center gap-1">
              <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
                <template #activator>
                  <RuiButton
                    color="primary"
                    variant="text"
                    size="sm"
                    class="!p-2"
                    icon
                    @click="applyFilter(filters)"
                  >
                    <RuiIcon size="16" name="corner-left-up-line" />
                  </RuiButton>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.apply') }}
                </span>
              </RuiTooltip>

              <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
                <template #activator>
                  <RuiButton
                    color="primary"
                    variant="text"
                    size="sm"
                    class="!p-2"
                    icon
                    @click="deleteFilter(index)"
                  >
                    <RuiIcon size="16" name="delete-bin-5-line" />
                  </RuiButton>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.remove') }}
                </span>
              </RuiTooltip>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="p-4">
        <i18n path="table_filter.saved_filters.empty">
          <template #button>
            <RuiButton
              color="secondary"
              variant="text"
              size="sm"
              disabled
              class="inline-flex"
            >
              <RuiIcon size="16" name="play-list-add-line" />
            </RuiButton>
          </template>
        </i18n>
      </div>
    </VMenu>
  </div>
</template>

<style module lang="scss">
.add-tooltip {
  height: 1rem;
  overflow: hidden;

  &__wrapper {
    transition: 0.2s all;

    &--added {
      margin-top: -1rem;
    }
  }
}
</style>
