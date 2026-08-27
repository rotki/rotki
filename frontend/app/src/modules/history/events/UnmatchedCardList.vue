<script setup lang="ts" generic="T">
import type { TablePaginationData } from '@rotki/ui-library';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';

const selected = defineModel<string[]>('selected', { required: true });

// Never caps its own height, so the host must be a bounded flex column or the pager scrolls away.
const { items, rowKey, emptyDescription, highlighted, accented, loading } = defineProps<{
  items: T[];
  /** Stable identity of a card, and what the selection model stores. */
  rowKey: (item: T) => string;
  emptyDescription: string;
  /** Card that a deep link points at, highlighted the same way the table row is. */
  highlighted?: (item: T) => boolean;
  /** Card whose row cannot be matched, marked with a warning edge. */
  accented?: (item: T) => boolean;
  loading?: boolean;
}>();

defineSlots<{
  alert?: () => unknown;
  header: (props: { item: T }) => unknown;
  asset: (props: { item: T }) => unknown;
  /** One-line reason shown between the asset and the actions, e.g. why no match can exist. */
  warning?: (props: { item: T }) => unknown;
  actions: (props: { item: T }) => unknown;
}>();

/** Matches RuiDataTable's own default, so pinning a list does not change how much of it you see. */
const ITEMS_PER_PAGE = 10;

const { t } = useI18n({ useScope: 'global' });

const page = ref<number>(1);
const itemsPerPage = ref<number>(ITEMS_PER_PAGE);

const keys = computed<string[]>(() => items.map(item => rowKey(item)));

const pagination = computed<TablePaginationData>({
  get() {
    return {
      limit: get(itemsPerPage),
      limits: [10, 25, 50],
      page: get(page),
      total: items.length,
    };
  },
  set(value: TablePaginationData) {
    set(page, value.page);
    set(itemsPerPage, value.limit);
  },
});

const visibleItems = computed<T[]>(() => {
  const start = (get(page) - 1) * get(itemsPerPage);
  return items.slice(start, start + get(itemsPerPage));
});

/**
 * Counted against this list's own keys rather than the raw model: a refresh can drop a row
 * while its key is still selected, which would otherwise leave the header checkbox
 * indeterminate over a list where nothing is actually ticked.
 */
const selectedCount = computed<number>(() => get(keys).filter(key => get(selected).includes(key)).length);

const allSelected = computed<boolean>(() => get(keys).length > 0 && get(selectedCount) === get(keys).length);

const someSelected = computed<boolean>(() => get(selectedCount) > 0 && !get(allSelected));

function isSelected(item: T): boolean {
  return get(selected).includes(rowKey(item));
}

function toggle(item: T, value: boolean): void {
  const key = rowKey(item);
  set(selected, value ? [...get(selected), key] : get(selected).filter(entry => entry !== key));
}

/**
 * Driven by our own `allSelected` rather than the checkbox's emitted value: RuiCheckbox's
 * native input starts out `checked` even when the model says otherwise, so trusting the
 * payload made the first click on an empty list clear nothing instead of selecting.
 */
function toggleAll(value: boolean): void {
  const own = get(keys);
  set(selected, value
    ? [...new Set([...get(selected), ...own])]
    : get(selected).filter(entry => !own.includes(entry)));
}

watch(() => items.length, (length) => {
  const lastPage = Math.max(1, Math.ceil(length / get(itemsPerPage)));
  if (get(page) > lastPage) {
    set(page, lastPage);
  }
});
</script>

<template>
  <div
    class="flex-1 min-h-0 flex flex-col"
    data-testid="unmatched-card-list"
  >
    <div class="shrink-0">
      <slot name="alert" />
    </div>

    <div
      v-if="items.length > 0"
      class="shrink-0 flex items-center gap-2 px-2 py-1 border border-default rounded-t"
    >
      <RuiCheckbox
        :model-value="allSelected"
        :indeterminate="someSelected"
        color="primary"
        size="sm"
        class="!mt-0"
        hide-details
        :label="t('asset_movement_matching.card_list.select_all')"
        data-testid="unmatched-card-select-all"
        @update:model-value="toggleAll(!allSelected)"
      />
      <span
        v-if="selectedCount > 0"
        class="ml-auto text-caption text-rui-text-secondary"
      >
        {{ t('asset_movement_matching.card_list.selected_count', { count: selectedCount }, selectedCount) }}
      </span>
    </div>

    <ScrollableDialogContent fill>
      <div
        v-if="items.length === 0"
        class="flex flex-col items-center gap-2 py-8 border border-default rounded text-body-2 text-rui-text-secondary"
        data-testid="unmatched-card-empty"
      >
        <RuiProgress
          v-if="loading"
          circular
          variant="indeterminate"
          color="primary"
          size="24"
        />
        <template v-else>
          {{ emptyDescription }}
        </template>
      </div>

      <div
        v-else
        class="border-x border-b border-default rounded-b divide-y divide-rui-grey-200 dark:divide-rui-grey-800"
      >
        <div
          v-for="item in visibleItems"
          :key="rowKey(item)"
          class="flex gap-2 p-2 border-l-2 cursor-pointer transition-all hover:bg-rui-grey-50 dark:hover:bg-rui-grey-900"
          :class="[
            accented?.(item) ? 'border-l-rui-warning' : 'border-l-transparent',
            {
              '!bg-rui-warning/15': highlighted?.(item),
              '!bg-rui-primary/5': isSelected(item),
            },
          ]"
          data-testid="unmatched-card"
          :data-key="rowKey(item)"
          @click="toggle(item, !isSelected(item))"
        >
          <RuiCheckbox
            :model-value="isSelected(item)"
            color="primary"
            size="sm"
            class="!mt-0"
            hide-details
            @click.stop
            @update:model-value="toggle(item, $event ?? false)"
          />

          <div class="flex-1 min-w-0 flex flex-col gap-1">
            <slot
              name="header"
              :item="item"
            />
            <slot
              name="warning"
              :item="item"
            />

            <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1">
              <slot
                name="asset"
                :item="item"
              />
              <!-- the action line owns its own clicks: acting on a card must not also select it -->
              <div
                class="ml-auto"
                @click.stop
              >
                <slot
                  name="actions"
                  :item="item"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </ScrollableDialogContent>

    <RuiTablePagination
      v-if="items.length > itemsPerPage"
      v-model="pagination"
      dense
      class="shrink-0 mt-2"
      data-testid="unmatched-card-pagination"
    />
  </div>
</template>
