<script lang="ts" setup>
import type { SavedFilterLocation, SearchMatcher, Suggestion } from '@/types/filtering';
import { isEqual } from 'es-toolkit';
import SuggestedItem from '@/components/table-filter/SuggestedItem.vue';
import { useSavedFilter } from '@/composables/filters/saved';
import { useMessageStore } from '@/store/message';

const props = defineProps<{
  matchers: SearchMatcher<any>[];
  selection: Suggestion[];
  location: SavedFilterLocation;
  disabled: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:matches', matches: Suggestion[]): void;
}>();

const { t } = useI18n({ useScope: 'global' });

const { location, matchers, selection } = toRefs(props);

const open = ref<boolean>(false);

function applyFilter(filter: Suggestion[]) {
  emit('update:matches', filter);
  set(open, false);
}

const added = ref<boolean>(false);
const { isPending, start, stop } = useTimeoutFn(
  () => {
    set(added, false);
  },
  4000,
  { immediate: false },
);

const { start: startAnimation } = useTimeoutFn(
  () => {
    set(added, true);
    start();
  },
  100,
  { immediate: false },
);

function isAsset(searchKey: string): boolean {
  const found = get(matchers).find(({ key }) => key === searchKey);
  return !!found && 'asset' in found;
}

const { addFilter, deleteFilter, savedFilters } = useSavedFilter(location, isAsset);

const filtersList = computed(() => {
  const matcherKeys = get(matchers).map(item => item.key);
  return get(savedFilters)
    // Filter out keys that doesn't supported in the matchers list
    .map(filters => filters.filter(filter => matcherKeys.includes(filter.key)))
    .filter((filter, index, self) => {
      if (filter.length === 0)
        return false;
      // Sort the current filter array for consistent comparison
      const sortedFilter = filter.slice().sort((a, b) => a.key.localeCompare(b.key));
      // Check if this is the first occurrence of this filter combination
      return index === self.findIndex(f =>
        isEqual(sortedFilter, f.slice().sort((a, b) => a.key.localeCompare(b.key))),
      );
    });
});

const { setMessage } = useMessageStore();

async function addToSavedFilter() {
  const status = await addFilter(get(selection));
  if (status.success) {
    if (get(isPending)) {
      stop();
      set(added, false);
    }
    startAnimation();
  }
  else {
    setMessage({
      description: status.message,
      success: false,
      title: t('table_filter.saved_filters.saving.title'),
    });
  }
}
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
          class="!p-2.5"
          icon
          :disabled="disabled || selection.length === 0"
          @click="addToSavedFilter()"
        >
          <RuiIcon
            size="20"
            name="lu-list-plus"
          />
        </RuiButton>
      </template>
      <div
        class="text-center"
        :class="$style['add-tooltip']"
      >
        <div
          class="h-4 transition-all"
          :class="{ '-mt-4': added }"
        >
          <div>
            {{ t('table_filter.saved_filters.actions.add') }}
          </div>
          <div class="text-rui-success-lighter">
            {{ t('table_filter.saved_filters.added') }}
          </div>
        </div>
      </div>
    </RuiTooltip>

    <RuiMenu
      v-model="open"
      :popper="{ placement: 'bottom-end' }"
      menu-class="max-w-[25rem] max-h-[32rem]"
    >
      <template #activator="{ attrs }">
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
              class="!p-2.5"
              icon
              v-bind="attrs"
            >
              <RuiIcon
                size="20"
                name="lu-list-filter"
              />
            </RuiButton>
          </template>
          <span>{{ t('table_filter.saved_filters.actions.list') }}</span>
        </RuiTooltip>
      </template>
      <div
        v-if="filtersList.length > 0"
        class="py-2"
      >
        <div
          v-for="(filters, index) in filtersList"
          :key="index"
        >
          <RuiDivider
            v-if="index > 0"
            class="my-1"
          />
          <div class="flex justify-between px-4">
            <div class="flex flex-wrap items-start pr-4 gap-1 my-0.5">
              <RuiChip
                v-for="(filter, filterIndex) in filters"
                :key="filterIndex"
                tile
                size="sm"
                class="font-medium !py-0"
              >
                <SuggestedItem
                  chip
                  :suggestion="filter"
                />
              </RuiChip>
            </div>
            <div class="flex items-center gap-1">
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
              >
                <template #activator>
                  <RuiButton
                    color="primary"
                    variant="text"
                    size="sm"
                    class="!p-2"
                    icon
                    @click="applyFilter(filters)"
                  >
                    <RuiIcon
                      size="16"
                      name="lu-corner-left-up"
                    />
                  </RuiButton>
                </template>
                <span>
                  {{ t('table_filter.saved_filters.actions.apply') }}
                </span>
              </RuiTooltip>

              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
              >
                <template #activator>
                  <RuiButton
                    color="primary"
                    variant="text"
                    size="sm"
                    class="!p-2"
                    icon
                    @click="deleteFilter(index)"
                  >
                    <RuiIcon
                      size="16"
                      name="lu-trash-2"
                    />
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
      <div
        v-else
        class="p-4"
      >
        <i18n-t
          scope="global"
          keypath="table_filter.saved_filters.empty"
        >
          <template #button>
            <RuiButton
              color="secondary"
              variant="text"
              size="sm"
              disabled
              class="inline-flex"
            >
              <RuiIcon
                size="16"
                name="lu-list-plus"
              />
            </RuiButton>
          </template>
        </i18n-t>
      </div>
    </RuiMenu>
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
